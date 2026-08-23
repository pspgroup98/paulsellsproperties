#!/usr/bin/env python3
"""
Import an approved editorial batch into the publishing pipeline.

Usage:
    python3 scripts/import_editorial_batch.py path/to/batch.json
    python3 scripts/import_editorial_batch.py path/to/batch.json --draft
    python3 scripts/import_editorial_batch.py path/to/batch.json --approve

Modes:
    (default)  Validate → show approval table → prompt for "yes" / "draft" / Ctrl+C
    --draft    Import all articles as status="draft" — no publication schedule,
               no prompt. Safe to run repeatedly without publishing anything.
    --approve  Non-interactive: skip the prompt, import as approved. Use only in
               tested automation contexts.

Safety contract:
    ALL validation runs before ANY file is written.
    A single hard failure aborts the entire batch — no partial imports.
    If three articles are supplied and one has an em dash, ZERO articles are imported.

batch_week:
    The ISO date of the MONDAY that begins the publication week.
    Example: "2026-08-24" → Monday Aug 24, Wednesday Aug 26, Friday Aug 28.
    The importer derives Mon/Wed/Fri publication dates from this anchor using
    Python's date arithmetic — it does not assume any relationship between the
    batch_week and the current calendar day.
"""

import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

import config as cfg_module
from html_builder import build_article_html
from validator import (
    scan_fields_for_em_dashes,
    scan_for_other_dashes,
    check_source_completeness,
    check_search_intent_overlap,
    check_slug_collision,
    validate_social_content,
)

# ── Constants ────────────────────────────────────────────────────────────────

REQUIRED_BATCH_FIELDS = ["schema_version", "batch_week", "articles"]
REQUIRED_ARTICLE_FIELDS = [
    "title", "slug", "category", "article_type", "body_html",
    "excerpt", "meta_description", "search_intent",
    "normalized_search_intent", "audiences", "geographic_focus",
    "content_type", "primary_keyword",
]
VALID_ARTICLE_TYPES = {"A", "B", "C"}
LA = ZoneInfo("America/Los_Angeles")

# Day-of-week numbers for Mon/Wed/Fri
PUB_WEEKDAYS = {0, 2, 4}  # Monday=0, Wednesday=2, Friday=4

# Months for display formatting
MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ── Scheduling helpers ───────────────────────────────────────────────────────

def _next_pub_slots(from_date: date, count: int = 3) -> list:
    """
    Return the next `count` Mon/Wed/Fri publication datetimes (10:00 AM LA) on or
    after `from_date`.

    Uses Python's date arithmetic exclusively — no assumptions about the relationship
    between from_date and the current calendar day.
    """
    slots = []
    d = from_date
    while len(slots) < count:
        if d.weekday() in PUB_WEEKDAYS:
            dt = datetime(d.year, d.month, d.day, 10, 0, 0, tzinfo=LA)
            slots.append(dt)
        d += timedelta(days=1)
    return slots


def _format_slot_header(dt: datetime) -> str:
    """e.g. 'MONDAY — August 24, 2026'"""
    day_name  = WEEKDAY_NAMES[dt.weekday()].upper()
    month     = MONTH_NAMES[dt.month]
    return f"{day_name} — {month} {dt.day}, {dt.year}"


def _format_date_display(dt: datetime) -> str:
    """e.g. 'August 24, 2026'"""
    return f"{MONTH_NAMES[dt.month]} {dt.day}, {dt.year}"


def _parse_batch_week(batch_week_str: str) -> date:
    """Parse batch_week ISO string (YYYY-MM-DD) into a date object."""
    try:
        return date.fromisoformat(batch_week_str)
    except (ValueError, TypeError):
        raise ValueError(f"batch_week '{batch_week_str}' is not a valid ISO date (expected YYYY-MM-DD)")


# ── Validation helpers ───────────────────────────────────────────────────────

def _validate_batch_schema(batch: dict) -> list:
    """Check required top-level fields. Returns list of error strings."""
    errors = []
    for field_name in REQUIRED_BATCH_FIELDS:
        if field_name not in batch:
            errors.append(f"Missing required top-level field: '{field_name}'")
    if "articles" in batch:
        if not isinstance(batch["articles"], list) or len(batch["articles"]) == 0:
            errors.append("'articles' must be a non-empty list")
    return errors


def _validate_single_article(article: dict, registry: list, blog_dir: Path, article_num: int,
                              schema_version: str = "1") -> tuple:
    """
    Validate one article dict from the batch.

    Returns:
        (errors: list[str], warnings: list[str])

    Errors are hard failures — any error aborts the entire batch.
    Warnings are informational — import proceeds with warnings displayed.
    """
    errors   = []
    warnings = []
    label    = f"Article {article_num} ('{article.get('title', article.get('slug', '?'))}')"

    # ── Required fields ──────────────────────────────────────────────────────
    for f in REQUIRED_ARTICLE_FIELDS:
        val = article.get(f)
        if val is None or val == "" or val == []:
            errors.append(f"{label}: missing required field '{f}'")

    # ── action_type: update_existing not supported yet ───────────────────────
    action_type = article.get("action_type", "new")
    if action_type == "update_existing":
        errors.append(
            f"{label}: action_type='update_existing' is not yet supported in Phase 3. "
            f"Remove this article from the batch or change action_type to 'new'."
        )

    # ── Em dash scan (per-field, hard failure) ───────────────────────────────
    em_findings = scan_fields_for_em_dashes(article)
    for finding in em_findings:
        errors.append(
            f"{label}: em dash (U+2014) found in field '{finding['field']}' "
            f"at position {finding['position']}:\n"
            f"          ...{finding['context']}..."
        )

    # ── En dash and other Unicode dashes (warnings) ──────────────────────────
    dash_warnings = scan_for_other_dashes(article)
    for w in dash_warnings:
        warnings.append(
            f"{label}: {w['char_name']} in field '{w['field']}' at position "
            f"{w['position']}: ...{w['context']}... — review if this is correct punctuation"
        )

    # ── Structural validation of body_html ───────────────────────────────────
    body = article.get("body_html", "")
    h1_count = len(re.findall(r"<h1[\s>]", body, re.IGNORECASE))
    if h1_count > 0:
        errors.append(
            f"{label}: body_html contains {h1_count} H1 tag(s). "
            f"H1 is rendered by the page template from the title field — "
            f"remove H1 tags from body_html."
        )
    h2_count = len(re.findall(r"<h2[\s>]", body, re.IGNORECASE))
    if h2_count == 0:
        errors.append(f"{label}: body_html has no H2 headings — at least one H2 is required")

    plain_text = re.sub(r"<[^>]+>", "", body)
    word_count = len(plain_text.split())
    if word_count < 600:
        errors.append(f"{label}: body word count too low: {word_count} words (minimum 600)")
    elif word_count < 900:
        warnings.append(f"{label}: body word count is {word_count} — below recommended minimum of 900")

    # ── article_type ─────────────────────────────────────────────────────────
    art_type = article.get("article_type", "")
    if art_type and art_type not in VALID_ARTICLE_TYPES:
        errors.append(f"{label}: invalid article_type '{art_type}' — must be A, B, or C")

    # ── Slug collision ────────────────────────────────────────────────────────
    slug = article.get("slug", "")
    if slug:
        collision = check_slug_collision(slug, registry, blog_dir)
        if collision:
            errors.append(f"{label}: {collision}")

    # ── Source completeness (warning) ─────────────────────────────────────────
    src_warnings = check_source_completeness(article)
    warnings.extend(f"{label}: {w}" for w in src_warnings)

    # ── Search intent overlap (warning) ──────────────────────────────────────
    overlap_warnings = check_search_intent_overlap(article, registry)
    warnings.extend(f"{label}: {w}" for w in overlap_warnings)

    # ── Schema v2: social content validation ─────────────────────────────────
    social_errors, social_warnings = validate_social_content(article, schema_version)
    errors.extend(social_errors)
    warnings.extend(social_warnings)

    return errors, warnings


# ── Backlog / watch-list merge ───────────────────────────────────────────────

def _merge_entries(current: list, updates: list, batch_week: str, entry_type: str) -> tuple:
    """
    Merge a list of updates into the current entry list.
    Matches by 'id' field. If an entry's id already exists, updates it in place.
    If id is absent or new, appends the entry with an auto-generated id.

    Returns (updated_list, stats_dict)
    """
    indexed = {e["id"]: i for i, e in enumerate(current) if "id" in e}
    result  = list(current)
    n_updated = 0
    n_new     = 0

    for j, upd in enumerate(updates):
        uid = upd.get("id")
        if uid and uid in indexed:
            result[indexed[uid]] = {**result[indexed[uid]], **upd}
            n_updated += 1
        else:
            if not uid:
                # Auto-generate a stable id from batch_week + index
                safe_week = batch_week.replace("-", "")
                uid = f"{safe_week}-{entry_type[:3]}-{j+1:03d}"
                upd = {**upd, "id": uid}
            result.append(upd)
            n_new += 1

    return result, {"updated": n_updated, "new": n_new}


# ── Registry entry builder ───────────────────────────────────────────────────

def _word_count(body_html: str) -> int:
    return len(re.sub(r"<[^>]+>", "", body_html).split())


def _build_registry_entry(article: dict, pub_dt: datetime, cfg: dict, status: str) -> dict:
    """
    Build a complete article-index.json entry from a package article.

    Maps package field names to registry field names, computes date strings,
    and sets lifecycle fields based on the import mode.
    """
    slug      = article["slug"]
    base_url  = cfg.get("site_base_url", "https://paulsellsproperties.com")
    blog_path = cfg.get("blog_path", "blog")
    date_iso  = pub_dt.strftime("%Y-%m-%d")
    date_disp = _format_date_display(pub_dt)

    # Pillar mapping: package uses pillar_relationship, registry uses pillar
    pillar_rel = article.get("pillar_relationship")
    pillar_val = None
    if pillar_rel == "pillar":
        pillar_val = slug
    elif isinstance(pillar_rel, str) and pillar_rel.startswith("supporting:"):
        pillar_val = pillar_rel.split(":", 1)[1]

    return {
        "slug":                   slug,
        "title":                  article["title"],
        "excerpt":                article.get("excerpt", ""),
        "url":                    f"{base_url}/{blog_path}/{slug}.html",
        "status":                 status,
        "scheduled_publish_at":   pub_dt.isoformat() if status == "approved" else None,
        "published_at":           None,
        "date_iso":               date_iso,
        "date_display":           date_disp,
        "category":               article["category"],
        "author":                 cfg.get("author_name", "Paul Adams II"),
        "article_type":           article.get("article_type", "B"),
        "primary_topic":          article.get("primary_topic") or article.get("primary_keyword", ""),
        "primary_keyword":        article.get("primary_keyword", ""),
        "secondary_topics":       article.get("secondary_keywords", []),
        "search_intent":          article.get("search_intent", ""),
        "normalized_search_intent": article.get("normalized_search_intent", ""),
        "geographic_focus":       article.get("geographic_focus", "Los Angeles"),
        "neighborhood":           article.get("neighborhood"),
        "audience":               article.get("audiences", []),
        "content_type":           article.get("content_type", ""),
        "content_freshness_type": article.get("content_freshness_type", ""),
        "evergreen":              article.get("content_freshness_type", "evergreen") == "evergreen",
        "pillar":                 pillar_val,
        "pillar_relationship":    pillar_rel,
        "action_type":            article.get("action_type", "new"),
        "tags":                   [],    # Tags not in package schema; add manually if desired
        "internal_links":         [s.get("url", "") for s in article.get("internal_link_suggestions", [])],
        "related_articles":       article.get("related_article_suggestions", []),
        "sources":                article.get("sources", []),
        "review_after":           article.get("review_after", ""),
        "last_reviewed":          date_iso,
        "word_count_approx":      _word_count(article.get("body_html", "")),
        # Schema v2: social content (None for v1 batches)
        "social_content":         article.get("social_content"),
    }


# ── Display helpers ───────────────────────────────────────────────────────────

_HR = "─" * 66


def _print_header():
    print()
    print("╔" + "═" * 64 + "╗")
    print("║       Paul Sells Properties — Editorial Import             ║")
    print("╚" + "═" * 64 + "╝")


def _print_validation_summary(all_errors: list, all_warnings: list):
    if all_errors:
        print(f"\n  ✗ {len(all_errors)} validation error(s) found:\n")
        for err in all_errors:
            for line in err.split("\n"):
                print(f"    {line}")
        if all_warnings:
            print(f"\n  ⚠  {len(all_warnings)} warning(s) (not shown — fix errors first)\n")
    else:
        print(f"\n  ✓ Validation passed — no hard failures")
        if all_warnings:
            print(f"\n  ⚠  {len(all_warnings)} warning(s):\n")
            for w in all_warnings:
                print(f"    • {w}")


def _print_approval_table(articles: list, slots: list, batch: dict):
    print(f"\n  {_HR}")
    print(f"  PUBLICATION SCHEDULE")
    print(f"  {_HR}")

    type_labels = {"A": "A — Timely / Market", "B": "B — Evergreen", "C": "C — Authority / Investment"}

    for i, (art, slot) in enumerate(zip(articles, slots)):
        print(f"\n  {_format_slot_header(slot)}")
        print(f"    Title:    {art.get('title', '?')}")
        print(f"    Slug:     {art.get('slug', '?')}")
        print(f"    Category: {art.get('category', '?')}")
        audiences_str = ", ".join(art.get("audiences", [])) or "—"
        print(f"    Audience: {audiences_str}")
        art_type = art.get("article_type", "?")
        print(f"    Type:     {type_labels.get(art_type, art_type)}")
        source_count = len(art.get("sources", []))
        print(f"    Sources:  {source_count}")

        # Show action type if non-standard
        if art.get("action_type", "new") != "new":
            print(f"    Action:   {art.get('action_type')}")

        # Past-date warning
        now_la = datetime.now(LA)
        if slot <= now_la:
            delta = now_la - slot
            hrs   = int(delta.total_seconds() // 3600)
            print(f"    ⚠  Note: scheduled date is {hrs}h in the past — will publish on next Mon/Wed/Fri run")

    backlog_count   = len(batch.get("backlog_updates", []))
    watch_count     = len(batch.get("watch_list_updates", []))
    print(f"\n  {_HR}")
    print(f"  Backlog additions / updates:    {backlog_count}")
    print(f"  Watch-list additions / updates: {watch_count}")
    print(f"  {_HR}")


# ── Main import logic ─────────────────────────────────────────────────────────

def run_import(batch_path: Path, mode: str = "interactive") -> bool:
    """
    Execute the full import pipeline.

    mode:
        "interactive" — show table, prompt for "yes" / "draft"
        "approve"     — import as approved without prompting
        "draft"       — import as draft without prompting

    Returns True on successful import, False on validation failure or cancel.
    Raises SystemExit on unrecoverable errors.
    """
    _print_header()

    # ── 1. Load and parse JSON ────────────────────────────────────────────────
    try:
        raw = batch_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"\n  ✗ Cannot read file: {exc}\n")
        return False

    try:
        batch = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"\n  ✗ Invalid JSON: {exc}\n")
        return False

    # ── 2. Top-level schema validation ────────────────────────────────────────
    print(f"\n  Batch file:  {batch_path}")
    schema_errors = _validate_batch_schema(batch)
    if schema_errors:
        print(f"\n  ✗ Schema validation failed:\n")
        for err in schema_errors:
            print(f"    {err}")
        print()
        return False

    articles      = batch["articles"]
    batch_week    = batch["batch_week"]
    schema_ver    = str(batch.get("schema_version", "1"))
    article_count = len(articles)
    print(f"  Batch week:  {batch_week}  ({article_count} article(s))  schema v{schema_ver}")

    # ── 3. Parse batch_week and compute publication slots ────────────────────
    try:
        bw_date = _parse_batch_week(batch_week)
    except ValueError as exc:
        print(f"\n  ✗ {exc}\n")
        return False

    # Warn if batch_week is not a Monday
    if bw_date.weekday() != 0:
        day_name = WEEKDAY_NAMES[bw_date.weekday()]
        print(
            f"\n  ⚠  batch_week {batch_week} is a {day_name}, not a Monday. "
            f"Publication slots will be the next Mon/Wed/Fri on or after this date."
        )

    slots = _next_pub_slots(bw_date, count=article_count)

    # ── 4. Load registry and config ───────────────────────────────────────────
    cfg      = cfg_module.load_config()
    registry = cfg_module.load_article_index()
    blog_dir = cfg_module.BLOG_DIR

    # ── 5. Validate all articles ──────────────────────────────────────────────
    all_errors   = []
    all_warnings = []

    # When checking for slug collisions within the batch, track slugs we've already seen
    # so two articles in the same batch don't use the same slug.
    seen_slugs_in_batch = set()

    for i, article in enumerate(articles):
        # Check for intra-batch slug duplicates before hitting registry check
        slug = article.get("slug", "")
        if slug in seen_slugs_in_batch:
            all_errors.append(
                f"Article {i+1} ('{article.get('title', slug)}'): "
                f"slug '{slug}' is duplicated within this batch"
            )
        if slug:
            seen_slugs_in_batch.add(slug)

        errors, warnings = _validate_single_article(
            article=article,
            registry=registry,
            blog_dir=blog_dir,
            article_num=i + 1,
            schema_version=schema_ver,
        )
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # ── 6. Report validation results ──────────────────────────────────────────
    _print_validation_summary(all_errors, all_warnings)

    if all_errors:
        print(f"  Correct the error(s) above in the batch file and re-run.\n")
        return False

    # ── 7. Show approval table ────────────────────────────────────────────────
    _print_approval_table(articles, slots, batch)

    # ── 8. Determine import mode ──────────────────────────────────────────────
    if mode == "draft":
        final_status = "draft"
        print(f"\n  --draft mode: importing as drafts (no publication schedule).\n")
    elif mode == "approve":
        final_status = "approved"
        print(f"\n  --approve mode: importing as approved.\n")
    else:
        # Interactive prompt
        print()
        print(f"  Type  yes    → import as approved (articles publish Mon/Wed/Fri)")
        print(f"        draft  → import as drafts (no publication schedule)")
        print(f"        Ctrl+C → cancel without writing any files")
        print()
        try:
            answer = input("  Your choice: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Cancelled — no files written.\n")
            return False

        if answer == "yes":
            final_status = "approved"
        elif answer == "draft":
            final_status = "draft"
        else:
            print(f"\n  Unrecognized input '{answer}' — cancelled. No files written.\n")
            return False

    # ── 9. All validation passed — now write files ────────────────────────────
    print(f"\n  Writing files...")

    cfg_module.APPROVED_BATCHES_DIR.mkdir(parents=True, exist_ok=True)

    new_entries = []

    for i, (article, slot) in enumerate(zip(articles, slots)):
        slug = article["slug"]

        # Build the dict html_builder expects (uses "headline" not "title")
        article_for_html = dict(article)
        article_for_html["headline"]     = article["title"]
        article_for_html["date_iso"]     = slot.strftime("%Y-%m-%d")
        article_for_html["date_display"] = _format_date_display(slot)

        # Write HTML file
        html_content = build_article_html(article_for_html, cfg)
        html_path    = blog_dir / f"{slug}.html"
        html_path.write_text(html_content, encoding="utf-8")
        print(f"    ✓ Written: blog/{slug}.html")

        # Build registry entry
        entry = _build_registry_entry(article, slot, cfg, final_status)
        new_entries.append(entry)

    # ── 10. Update article-index.json ─────────────────────────────────────────
    # Prepend new articles (newest-first ordering)
    updated_registry = new_entries + registry
    index_path = cfg_module.ARTICLE_INDEX_PATH
    index_path.write_text(json.dumps(updated_registry, indent=2), encoding="utf-8")
    print(f"    ✓ Updated: content-system/article-index.json ({len(new_entries)} article(s) added)")

    # ── 11. Merge backlog updates ─────────────────────────────────────────────
    backlog_updates = batch.get("backlog_updates", [])
    if backlog_updates:
        bl = cfg_module.load_backlog()
        updated_entries, bl_stats = _merge_entries(
            bl.get("entries", []), backlog_updates, batch_week, "bkl"
        )
        bl["entries"] = updated_entries
        cfg_module.BACKLOG_PATH.write_text(json.dumps(bl, indent=2), encoding="utf-8")
        print(f"    ✓ Updated: content-system/editorial-backlog.json "
              f"({bl_stats['new']} new, {bl_stats['updated']} updated)")

    # ── 12. Merge watch-list updates ──────────────────────────────────────────
    watch_updates = batch.get("watch_list_updates", [])
    if watch_updates:
        wl = cfg_module.load_watch_list()
        updated_entries, wl_stats = _merge_entries(
            wl.get("entries", []), watch_updates, batch_week, "wch"
        )
        wl["entries"] = updated_entries
        cfg_module.WATCH_LIST_PATH.write_text(json.dumps(wl, indent=2), encoding="utf-8")
        print(f"    ✓ Updated: content-system/editorial-watch-list.json "
              f"({wl_stats['new']} new, {wl_stats['updated']} updated)")

    # ── 13. Archive the batch ─────────────────────────────────────────────────
    archive_path = cfg_module.APPROVED_BATCHES_DIR / f"{batch_week}.json"
    shutil.copy2(batch_path, archive_path)
    print(f"    ✓ Archived: content-system/approved-batches/{batch_week}.json")

    # ── 14. Final report ──────────────────────────────────────────────────────
    print()
    print(f"  {_HR}")
    if final_status == "approved":
        print(f"  Import complete — {len(new_entries)} article(s) approved and scheduled.")
        print(f"  Run 'git add' and commit when ready. Articles publish Mon/Wed/Fri at 10 AM PT.")
    else:
        print(f"  Import complete — {len(new_entries)} article(s) saved as drafts.")
        print(f"  Set status='approved' and scheduled_publish_at in article-index.json to publish.")
    print(f"  {_HR}")
    print()

    return True


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    batch_file = Path(args[0])
    if not batch_file.exists():
        print(f"\n  ✗ File not found: {batch_file}\n")
        sys.exit(1)

    # Determine mode from flags
    if "--draft" in args:
        mode = "draft"
    elif "--approve" in args:
        mode = "approve"
    else:
        mode = "interactive"

    success = run_import(batch_file, mode=mode)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
