"""
Weekly editorial automation — main entry point.

Invoked by .github/workflows/generate-articles.yml (Sundays at 8 AM PT).

This script:
  1. Researches topics via OpenAI.
  2. Generates up to 3 articles.
  3. Validates and builds article HTML files.
  4. Adds articles to article-index.json with status='approved' and
     auto-scheduled Mon/Wed/Fri publish timestamps.
  5. Creates a PR for Paul to review and merge.

This script does NOT update the homepage, blog archive, sitemap, or RSS.
Those surfaces are rebuilt by publish_scheduled.py when each article
actually publishes.

Environment variables:
  OPENAI_API_KEY        Required.
  DRY_RUN               Set to "true" to research and generate without writing files or creating a PR.
  OPENAI_MODEL          Override writing model (default from config.json).
  OPENAI_RESEARCH_MODEL Override research model (default from config.json).
"""
import json
import os
import sys
import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Add scripts/ to path so imports work when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

import openai

import config as cfg_module
from topic_research import research_topics
from article_generator import generate_article, request_em_dash_correction
from validator import validate_article, check_slug_collision
from html_builder import build_article_html, format_display_date
from site_updater import update_article_index

REPO_ROOT    = Path(__file__).parent.parent
MAX_ARTICLES = 3   # hard safety limit — never exceed in one run
PUB_HOUR     = 10  # 10:00 AM LA time
PUB_DAYS     = {0, 2, 4}  # Mon=0, Wed=2, Fri=4


# ── Publication slot calculator ───────────────────────────────────────────────

def _next_pub_slots(from_date: date, count: int = MAX_ARTICLES) -> list:
    """
    Return the next `count` Monday / Wednesday / Friday datetimes at PUB_HOUR AM
    in America/Los_Angeles, starting the day AFTER from_date (typically Sunday).
    DST is handled automatically by ZoneInfo.
    """
    la    = ZoneInfo("America/Los_Angeles")
    slots = []
    day   = from_date
    while len(slots) < count:
        day += timedelta(days=1)
        if day.weekday() in PUB_DAYS:
            slots.append(datetime(day.year, day.month, day.day, PUB_HOUR, 0, 0, tzinfo=la))
    return slots


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    cfg                  = cfg_module.load_config()
    article_index        = cfg_module.load_article_index()
    manual_topics        = cfg_module.load_manual_topics()
    editorial_guidelines = cfg_module.load_editorial_guidelines()
    today                = date.today()

    # Calculate publication slots (Mon/Wed/Fri following today/Sunday)
    pub_slots = _next_pub_slots(today, MAX_ARTICLES)

    print(f"\n{'=' * 60}")
    print(f"Paul Sells Properties — Weekly Editorial Run")
    print(f"Generation date: {today.isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    print(f"Writing model: {cfg['writing_model']}")
    print(f"Existing articles: {len(article_index)}")
    print(f"Manual topics queued: {len(manual_topics)}")
    print(f"Scheduled publication slots:")
    for slot in pub_slots:
        print(f"  {slot.strftime('%A %Y-%m-%d %H:%M %Z')}")
    print(f"{'=' * 60}\n")

    # ── Step 1: Topic research ────────────────────────────────────────────────
    print("STEP 1: Researching topics...")
    selected_topics = research_topics(
        client=client,
        existing_articles=article_index,
        cfg=cfg,
        manual_topics=manual_topics,
    )

    if not selected_topics:
        print("ERROR: Topic research returned no candidates. Aborting.")
        sys.exit(1)

    selected_topics = selected_topics[:MAX_ARTICLES]
    print(f"\nSelected {len(selected_topics)} topic(s):")
    for i, t in enumerate(selected_topics):
        print(f"  {i+1}. [{t.get('article_type','?')}] {t.get('suggested_headline', t.get('topic','?'))}")

    # ── Step 2: Generate, validate, build ────────────────────────────────────
    approved_articles   = []
    failed_articles     = []
    pr_article_summaries = []

    for i, topic in enumerate(selected_topics):
        print(f"\n{'─' * 40}")
        print(f"ARTICLE {i+1}/{len(selected_topics)}: {topic.get('suggested_headline', topic.get('topic',''))}")
        print(f"{'─' * 40}")

        # Assign publication slot
        pub_slot     = pub_slots[i] if i < len(pub_slots) else pub_slots[-1]
        pub_date_iso = pub_slot.date().isoformat()
        pub_display  = pub_slot.strftime("%B %-d, %Y")

        # Generate
        try:
            article = generate_article(
                client=client,
                topic=topic,
                editorial_guidelines=editorial_guidelines,
                existing_articles=article_index,
                cfg=cfg,
            )
        except Exception as e:
            print(f"  ERROR: Generation failed: {e}")
            failed_articles.append({"topic": topic, "reason": str(e)})
            continue

        # Slug collision check
        collision = check_slug_collision(article["slug"], article_index, cfg_module.BLOG_DIR)
        if collision:
            print(f"  FAIL: {collision}")
            failed_articles.append({"topic": topic, "article": article, "reason": collision})
            continue

        # Date fields — use the scheduled publication date, not today
        article["date_iso"]             = pub_date_iso
        article["date_display"]         = pub_display
        article["status"]               = "approved"
        article["scheduled_publish_at"] = pub_slot.isoformat()
        article["published_at"]         = None
        article["site_base_url"]        = cfg.get("site_base_url", "https://paulsellsproperties.com")
        article["author_name"]          = cfg.get("author_name", "Paul Adams II")

        # Validate
        result   = validate_article(article)
        attempts = 0
        while result.em_dash_fail and attempts < cfg.get("max_revision_attempts", 2):
            attempts += 1
            print(f"  Em dash found — requesting correction (attempt {attempts})...")
            article = request_em_dash_correction(client, article, editorial_guidelines, cfg)
            result  = validate_article(article)

        if not result.passed:
            print(f"  FAIL — validation did not pass after corrections:")
            print(f"  {result.summary()}")
            failed_articles.append({
                "topic":   topic,
                "article": article,
                "reason":  result.summary(),
            })
            continue

        if result.quality_warnings or result.structural_warnings:
            print(f"  WARNINGS (article will proceed):")
            for w in result.quality_warnings + result.structural_warnings:
                print(f"    • {w}")

        # Build HTML (using the scheduled date for display)
        article_html  = build_article_html(article, cfg)
        article_path  = cfg_module.BLOG_DIR / f"{article['slug']}.html"

        if not dry_run:
            article_path.write_text(article_html, encoding="utf-8")
            print(f"  ✓ Written: blog/{article['slug']}.html")
            print(f"  ✓ Scheduled: {pub_slot.strftime('%A %Y-%m-%d %H:%M %Z')}")
        else:
            print(f"  [DRY RUN] Would write: blog/{article['slug']}.html")
            print(f"  [DRY RUN] Would schedule: {pub_slot.strftime('%A %Y-%m-%d %H:%M %Z')}")
            (REPO_ROOT / "content-system" / f"_dryrun_{article['slug']}.html").write_text(
                article_html, encoding="utf-8"
            )

        approved_articles.append(article)
        pr_article_summaries.append(_article_summary(article, result, i + 1, pub_slot))
        print(f"  ✓ Article {i+1} ready: {article['headline']}")

    # ── Step 3: Registry update (not public surfaces) ────────────────────────
    print(f"\n{'─' * 40}")
    print(f"STEP 3: Updating article registry ({len(approved_articles)} article(s))...")
    print(f"  (Homepage, archive, sitemap, and RSS are rebuilt at publish time by")
    print(f"   publish_scheduled.py — not here.)")

    if not approved_articles:
        print("No approved articles — no registry update needed.")
        _write_pr_body([], failed_articles, dry_run)
        sys.exit(0 if not failed_articles else 1)

    if not dry_run:
        try:
            update_article_index(approved_articles, cfg_module.ARTICLE_INDEX_PATH)
            manual_used = sum(1 for a in approved_articles if a.get("is_manual"))
            if manual_used:
                cfg_module.consume_manual_topics(manual_used)
        except Exception as e:
            print(f"ERROR during registry update: {e}")
            sys.exit(1)
    else:
        print("[DRY RUN] Skipping article-index.json update")

    # ── Step 4: PR body ──────────────────────────────────────────────────────
    _write_pr_body(pr_article_summaries, failed_articles, dry_run)

    print(f"\n{'=' * 60}")
    print(f"Run complete: {len(approved_articles)} article(s) approved, "
          f"{len(failed_articles)} failed")
    print(f"{'=' * 60}\n")

    if failed_articles:
        sys.exit(1)


def _article_summary(article: dict, result, num: int, pub_slot: datetime) -> str:
    em_status = "PASS" if not result.em_dash_fail else "FAIL"
    checks = [
        f"Em dash: {em_status}",
        f"Slug: PASS",
        f"Metadata: {'PASS' if article.get('meta_description') else 'FAIL'}",
        f"HTML structure: {'PASS' if not result.structural_errors else 'FAIL — ' + '; '.join(result.structural_errors)}",
        f"Internal links: {len(article.get('internal_links_used', []))} added",
    ]
    warnings = result.quality_warnings + result.structural_warnings
    links    = "\n".join(
        f"  - [{lnk.get('anchor_text','')}]({lnk.get('url','')})"
        for lnk in article.get("internal_links_used", [])
    ) or "  None"
    sources  = "\n".join(f"  - {s}" for s in article.get("key_sources", [])) or "  None specified"
    sched    = pub_slot.strftime("%A %Y-%m-%d %H:%M %Z")

    return textwrap.dedent(f"""
### Article {num}: {article['headline']}

| Field | Value |
|-------|-------|
| Slug | `{article['slug']}` |
| Category | {article.get('category', '')} |
| Type | {article.get('article_type', '')} |
| Primary keyword | {article.get('primary_keyword', '')} |
| Word count (est.) | ~{article.get('word_count_estimate', 0)} |
| Scheduled publication | {sched} |

> **To reschedule:** Edit `content-system/article-index.json` in this PR — change
> `scheduled_publish_at` before merging. To cancel entirely, set `status` to `"draft"`.

**Why this topic:** {article.get('topic_rationale', 'See topic research output')}

**Sources used:**
{sources}

**Internal links added:**
{links}

**Validation:**
""") + "\n".join(f"- {c}" for c in checks) + (
        f"\n\n**Warnings:**\n" + "\n".join(f"- {w}" for w in warnings) if warnings else ""
    )


def _write_pr_body(summaries: list, failures: list, dry_run: bool) -> None:
    today     = date.today()
    intro     = "**DRY RUN — no files were written to the repository.**\n\n" if dry_run else ""
    fail_sect = ""
    if failures:
        fail_sect = "\n\n---\n\n## Failed Articles\n\n"
        for f in failures:
            fail_sect += (
                f"- **{f['topic'].get('suggested_headline', f['topic'].get('topic','?'))}**"
                f" — {f['reason']}\n"
            )

    body = f"""{intro}## Weekly Articles — {today.strftime('%B %d, %Y')}

This PR contains {len(summaries)} article(s) generated by the automated editorial system.
Each article is **approved** with a scheduled Mon/Wed/Fri publication timestamp.

**How publication works:**
- Merging this PR commits the article HTML files and updates `article-index.json`.
- The `publish-scheduled` workflow runs automatically on the scheduled day and makes
  the article public (homepage, archive, sitemap, RSS).
- No further action is required after merging.

**To reschedule or cancel:** Edit `content-system/article-index.json` before merging.

{"".join(summaries)}{fail_sect}

---

**Checklist before merging:**
- [ ] Read each article in full
- [ ] Verify all facts and sources are accurate
- [ ] Confirm no em dashes (automated check passed)
- [ ] Confirm voice and tone match the site
- [ ] Spot-check internal links resolve correctly
- [ ] Verify scheduled_publish_at dates are correct
- [ ] Approve and merge when satisfied

*Generated by the Paul Sells Properties editorial automation system.*
"""
    pr_body_path = Path("/tmp/pr_body.md")
    pr_body_path.write_text(body, encoding="utf-8")
    print(f"[run_weekly_batch] PR body written to {pr_body_path}")


if __name__ == "__main__":
    main()
