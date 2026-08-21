"""
Scheduled publication script.

Runs Mon / Wed / Fri at 10:00 AM America/Los_Angeles via publish-scheduled.yml.
Can also be triggered manually via workflow_dispatch at any time.

DST handling
------------
The workflow cron fires at both 17:00 UTC and 18:00 UTC on publication days,
covering 10:00 AM under both PDT (UTC-7) and PST (UTC-8). This script is the
sole authority on eligibility: it reads the current time via ZoneInfo so
that no article can publish at 9:00 AM simply because clocks changed.

Idempotency
-----------
Running this script twice in the same session is safe:
  • Only articles with status='approved' are considered. Once an article is
    transitioned to status='published', subsequent runs skip it.
  • git diff --cached --quiet in the workflow step skips the commit when
    no files changed — no duplicate commits, no redundant GitHub Pages deploys.

Responsibility:
  1. Find 'approved' articles whose scheduled_publish_at <= now (America/Los_Angeles).
  2. Set status → 'published', record published_at as a timezone-aware ISO string.
  3. Rebuild all public surfaces: homepage, blog archive, sitemap, RSS.
  4. Save updated article-index.json.

This script does NOT:
  - Call OpenAI or any external AI service.
  - Generate or modify article copy.
  - Create PRs.
  - Modify article HTML files.

Exit codes:
  0 — ran successfully (may or may not have published anything)
  1 — fatal error
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Ensure scripts/ is on the path regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

import config as cfg_module
from site_updater import (
    _la_now,
    _parse_dt,
    update_homepage,
    update_blog_archive,
    update_sitemap_full,
    update_rss_full,
)

REPO_ROOT = Path(__file__).parent.parent


def main() -> None:
    la      = ZoneInfo("America/Los_Angeles")
    now_la  = datetime.now(la)
    cfg     = cfg_module.load_config()
    index_path = cfg_module.ARTICLE_INDEX_PATH

    print(f"\n{'=' * 60}")
    print(f"Paul Sells Properties — Scheduled Publication Run")
    print(f"Time (LA): {now_la.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"{'=' * 60}\n")

    # Load registry
    if not index_path.exists():
        print("ERROR: article-index.json not found.")
        sys.exit(1)

    with open(index_path) as f:
        article_index: list = json.load(f)

    # Identify eligible approved articles
    newly_published = []
    for article in article_index:
        if article.get("status") != "approved":
            continue

        sched = article.get("scheduled_publish_at")
        if not sched:
            print(f"  WARNING: '{article['slug']}' is approved but has no "
                  f"scheduled_publish_at — skipping")
            continue

        try:
            pub_dt = _parse_dt(sched)
        except (ValueError, TypeError):
            print(f"  WARNING: invalid scheduled_publish_at for '{article['slug']}': "
                  f"{sched!r} — skipping")
            continue

        if pub_dt <= now_la:
            # Check that the article HTML file actually exists
            html_path = cfg_module.BLOG_DIR / f"{article['slug']}.html"
            if not html_path.exists():
                print(f"  WARNING: '{article['slug']}' is eligible but "
                      f"blog/{article['slug']}.html is missing — skipping "
                      f"(merge the PR that adds the file first)")
                continue

            article["status"]       = "published"
            article["published_at"] = now_la.isoformat()
            newly_published.append(article)
            print(f"  Publishing: {article['slug']}  "
                  f"(scheduled {sched})")
        else:
            remaining = pub_dt - now_la
            hrs = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            print(f"  Pending:    {article['slug']}  "
                  f"(publishes in {hrs}h {mins}m)")

    if not newly_published:
        print("\nNo articles eligible for publication. No changes made.")
        sys.exit(0)

    # Save updated registry first (so surfaces are rebuilt from correct state)
    with open(index_path, "w") as f:
        json.dump(article_index, f, indent=2)
    print(f"\n[publish_scheduled] article-index.json updated")

    # Rebuild all public surfaces
    print("[publish_scheduled] Rebuilding public surfaces...\n")

    update_homepage(article_index, cfg_module.HOMEPAGE_PATH, now_la)
    update_blog_archive(article_index, cfg_module.BLOG_INDEX_PATH, now_la)
    update_sitemap_full(article_index, cfg_module.SITEMAP_PATH, cfg, now_la)
    update_rss_full(article_index, cfg_module.RSS_PATH, cfg, now_la)

    print(f"\n{'=' * 60}")
    print(f"Published {len(newly_published)} article(s):")
    for a in newly_published:
        print(f"  • {a['slug']}  (published_at: {a['published_at']})")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
