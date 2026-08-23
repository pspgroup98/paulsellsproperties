#!/usr/bin/env python3
"""
One-time migration: inject analytics script + fix footer links + fix Calendly
in all existing static HTML files.

Run once:
    python3 scripts/migrate_analytics.py

Safe to re-run (idempotent — skips files that already have analytics tag).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Files to skip (templates, non-public, or newly created by this session)
SKIP_SLUGS = {
    "article-template.html",
    "privacy.html",   # already correct
    "terms.html",     # already correct
}


def classify(html_path: Path) -> str:
    """Return 'root', 'blog', or 'neighborhood' based on file location."""
    parts = html_path.relative_to(ROOT).parts
    if len(parts) == 1:
        return "root"
    if parts[0] == "blog":
        return "blog"
    if parts[0] == "neighborhoods":
        return "neighborhood"
    return "root"


def analytics_tag(depth: str) -> str:
    prefix = "../" if depth in ("blog", "neighborhood") else ""
    return f'<script src="{prefix}assets/js/analytics.js" defer></script>'


def footer_links_root() -> str:
    return (
        '<a href="terms.html">Terms</a>\n'
        '          <a href="privacy.html">Privacy</a>\n'
        '          <a href="https://www.hud.gov/program_offices/fair_housing_equal_opp/fair_housing_act_overview" target="_blank" rel="noopener">Fair Housing</a>'
    )


def footer_links_subdir() -> str:
    return (
        '<a href="../terms.html">Terms</a>\n'
        '          <a href="../privacy.html">Privacy</a>\n'
        '          <a href="https://www.hud.gov/program_offices/fair_housing_equal_opp/fair_housing_act_overview" target="_blank" rel="noopener">Fair Housing</a>'
    )


CALENDLY_CSS_TAG = '<link href="https://assets.calendly.com/assets/external/widget.css" rel="stylesheet">'
CALENDLY_JS_TAG  = '<script src="https://assets.calendly.com/assets/external/widget.js" async></script>'
CALENDLY_INIT_OLD = "Calendly.initPopupWidget({url:'https://calendly.com/adams2paul'})"
CALENDLY_INIT_NEW = "PSP.openCalendly('https://calendly.com/adams2paul')"


def migrate_file(html_path: Path) -> bool:
    """
    Apply all migrations to a single HTML file.
    Returns True if the file was modified.
    """
    original = html_path.read_text(encoding="utf-8")
    content = original
    depth = classify(html_path)

    # ── 1. Add analytics script (before </body>) ─────────────────────────────
    tag = analytics_tag(depth)
    if tag not in content:
        # Insert before </body>
        content = content.replace("</body>", f"{tag}\n</body>")

    # ── 2. Fix footer dead links ──────────────────────────────────────────────
    # Patterns seen in existing files:
    old_footer_patterns = [
        # The exact block in the existing static files
        '<a href="#">Terms</a>\n          <a href="#">Privacy</a>\n          <a href="#">Fair Housing</a>',
        '<a href="#">Terms</a>\n          <a href="#">Privacy</a>',
        # Accessibility variant
        '<a href="#">Terms</a>\n          <a href="#">Privacy</a>\n          <a href="#">Accessibility</a>\n          <a href="#">Fair Housing</a>',
    ]
    if depth in ("blog", "neighborhood"):
        new_footer = footer_links_subdir()
    else:
        new_footer = footer_links_root()

    for old_pattern in old_footer_patterns:
        if old_pattern in content:
            content = content.replace(old_pattern, new_footer)
            break  # only one pattern will match per file

    # ── 3. Remove eager Calendly CSS and JS tags ──────────────────────────────
    content = content.replace(CALENDLY_CSS_TAG + "\n", "")
    content = content.replace(CALENDLY_CSS_TAG, "")
    content = content.replace(CALENDLY_JS_TAG + "\n", "")
    content = content.replace(CALENDLY_JS_TAG, "")

    # ── 4. Replace Calendly.initPopupWidget with PSP.openCalendly ─────────────
    content = content.replace(CALENDLY_INIT_OLD, CALENDLY_INIT_NEW)

    # ── 5. Write back if changed ──────────────────────────────────────────────
    if content != original:
        html_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    html_files = sorted(ROOT.rglob("*.html"))
    modified = []
    skipped = []
    unchanged = []

    for f in html_files:
        if f.name in SKIP_SLUGS:
            skipped.append(f)
            continue
        if ".git" in f.parts:
            continue
        changed = migrate_file(f)
        if changed:
            modified.append(f)
        else:
            unchanged.append(f)

    print(f"\nMigration complete")
    print(f"  Modified:  {len(modified)}")
    print(f"  Unchanged: {len(unchanged)}")
    print(f"  Skipped:   {len(skipped)}")
    if modified:
        print("\nModified files:")
        for f in modified:
            print(f"  {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
