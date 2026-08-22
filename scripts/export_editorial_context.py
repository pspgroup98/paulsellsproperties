#!/usr/bin/env python3
"""
Export a compact editorial context file for use in ChatGPT's weekly research session.

Usage:
    python3 scripts/export_editorial_context.py
    python3 scripts/export_editorial_context.py --output path/to/context.json

Output:
    content-system/editorial-context.json  (default, overwritten each run)

What this generates:
    A JSON file containing:
    - Published and scheduled articles (metadata only — no body HTML)
    - Editorial backlog entries
    - Watch-list entries
    - Internal site page inventory for internal-link suggestions
    - Audience taxonomy and content category list

How to use it:
    1. Run this script each Sunday before opening ChatGPT.
    2. Open content-system/editorial-context.json.
    3. Copy its entire contents.
    4. In ChatGPT, paste the context along with the weekly research prompt from
       content-system/CHATGPT_EDITORIAL_PROMPT.md.
    5. ChatGPT will use the context to avoid duplicate search intent, build on
       existing content, and make accurate internal-link suggestions.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg_module

LA = ZoneInfo("America/Los_Angeles")

# ── Known site pages for internal-link suggestions ───────────────────────────
# These are the non-blog pages ChatGPT may suggest linking to.
SITE_PAGES = [
    {"name": "Home",                   "url": "/index.html",                         "slug": "home"},
    {"name": "Property Search",        "url": "/property-search.html",               "slug": "property-search"},
    {"name": "Buying & Selling Tips",  "url": "/buying-selling-tips.html",           "slug": "buying-selling-tips"},
    {"name": "About Paul Adams II",    "url": "/about.html",                         "slug": "about"},
    {"name": "Contact",                "url": "/contact.html",                       "slug": "contact"},
    {"name": "Blog / Insights",        "url": "/blog/index.html",                    "slug": "blog-index"},
    {"name": "Home Valuation",         "url": "/home-valuation.html",               "slug": "home-valuation"},
    {"name": "Neighborhoods Index",    "url": "/neighborhoods/index.html",           "slug": "neighborhoods"},
    {"name": "Beverly Hills",          "url": "/neighborhoods/beverly-hills.html",   "slug": "beverly-hills"},
    {"name": "Bel Air",                "url": "/neighborhoods/bel-air.html",         "slug": "bel-air"},
    {"name": "Hollywood Hills",        "url": "/neighborhoods/hollywood-hills.html", "slug": "hollywood-hills"},
    {"name": "Santa Monica",           "url": "/neighborhoods/santa-monica.html",    "slug": "santa-monica"},
    {"name": "Venice",                 "url": "/neighborhoods/venice.html",          "slug": "venice"},
    {"name": "Silver Lake",            "url": "/neighborhoods/silver-lake.html",     "slug": "silver-lake"},
    {"name": "West Hollywood",         "url": "/neighborhoods/west-hollywood.html",  "slug": "west-hollywood"},
    {"name": "Los Feliz",              "url": "/neighborhoods/los-feliz.html",       "slug": "los-feliz"},
    {"name": "Studio City",            "url": "/neighborhoods/studio-city.html",     "slug": "studio-city"},
    {"name": "Sherman Oaks",           "url": "/neighborhoods/sherman-oaks.html",    "slug": "sherman-oaks"},
    {"name": "Encino",                 "url": "/neighborhoods/encino.html",          "slug": "encino"},
    {"name": "Highland Park",          "url": "/neighborhoods/highland-park.html",   "slug": "highland-park"},
    {"name": "West Adams",             "url": "/neighborhoods/west-adams.html",      "slug": "west-adams"},
    {"name": "Pacific Palisades",      "url": "/neighborhoods/pacific-palisades.html", "slug": "pacific-palisades"},
    {"name": "Downtown LA",            "url": "/neighborhoods/downtown-la.html",     "slug": "downtown-la"},
]

# ── Editorial taxonomy ────────────────────────────────────────────────────────
AUDIENCE_TAXONOMY = [
    "buyers",
    "first-time buyers",
    "sellers",
    "investors",
    "landlords",
    "rental property owners",
    "duplex owners",
    "condo owners",
    "homeowners",
    "move-up buyers",
    "luxury buyers",
    "lifestyle buyers",
]

CONTENT_TYPES = [
    "evergreen",            # Durable topics: buying guides, explanations, strategy
    "news",                 # Breaking / time-sensitive developments
    "regulatory",           # Laws, ordinances, policy changes
    "market_data",          # Market statistics, trends, forecasts
    "strategy-guide",       # Decision frameworks, analytical guides
    "evergreen-guide",      # Extended reference guides
    "market-analysis",      # In-depth market analysis
    "market-insight",       # Market observations with strategic context
    "legal-regulatory",     # Legal requirements and compliance
    "lifestyle",            # Lifestyle, neighborhood character, quality of life
    "periodic",             # Seasonal / recurring topics (spring market, etc.)
]

CONTENT_FRESHNESS_TYPES = [
    "evergreen",            # Valid indefinitely with minor updates
    "news",                 # Valid for days to weeks
    "periodic",             # Valid for a season or year
    "regulatory",           # Valid until the law/policy changes
    "market_data",          # Valid until next data release
]

ARTICLE_TYPES = {
    "A": "Timely / Market Intelligence — current events, legislation, market shifts",
    "B": "Evergreen Search / Consumer Education — durable guides, financing, neighborhoods",
    "C": "Authority / Investment — analytical, investment strategy, multifamily",
}

CATEGORIES = [
    "Buyer's Guide",
    "Buyer Strategy",
    "Seller Strategy",
    "Market Analysis",
    "Investor Strategy",
    "Real Estate Investing",
    "Landlord & Rental Laws",
    "Condo / HOA",
    "Neighborhood",
    "Lifestyle",
    "Financing",
    "Multifamily",
]


def _article_metadata(article: dict) -> dict:
    """Return a compact metadata dict for one article (no body HTML)."""
    return {
        "slug":                     article.get("slug"),
        "title":                    article.get("title"),
        "excerpt":                  article.get("excerpt", ""),
        "category":                 article.get("category"),
        "article_type":             article.get("article_type"),
        "primary_keyword":          article.get("primary_keyword"),
        "search_intent":            article.get("search_intent"),
        "normalized_search_intent": article.get("normalized_search_intent"),
        "audience":                 article.get("audience", []),
        "geographic_focus":         article.get("geographic_focus"),
        "content_type":             article.get("content_type"),
        "content_freshness_type":   article.get("content_freshness_type"),
        "evergreen":                article.get("evergreen"),
        "pillar":                   article.get("pillar"),
        "pillar_relationship":      article.get("pillar_relationship"),
        "related_articles":         article.get("related_articles", []),
        "date_iso":                 article.get("date_iso"),
        "review_after":             article.get("review_after"),
        "status":                   article.get("status"),
    }


def build_context(output_path=None) -> Path:
    """
    Build the editorial context JSON and write it to output_path.
    Returns the path where the file was written.
    """
    now_la = datetime.now(LA)
    registry = cfg_module.load_article_index()
    backlog  = cfg_module.load_backlog()
    watch    = cfg_module.load_watch_list()
    cfg      = cfg_module.load_config()

    if output_path is None:
        output_path = cfg_module.EDITORIAL_CONTEXT_PATH

    # Split registry into published and scheduled
    published  = []
    scheduled  = []
    for art in registry:
        status = art.get("status", "")
        if status == "published":
            published.append(_article_metadata(art))
        elif status == "approved":
            scheduled.append(_article_metadata(art))

    # Collect all categories and audience values actually in use
    categories_in_use = sorted({a.get("category") for a in registry if a.get("category")})
    audiences_in_use  = sorted({
        aud
        for a in registry
        for aud in (a.get("audience") or [])
    })

    context = {
        "_generated_at": now_la.isoformat(),
        "_note": (
            "Paste this entire JSON into ChatGPT before beginning weekly editorial research. "
            "It tells ChatGPT what has been published, what is scheduled, what is in the "
            "backlog, and what developing stories to watch — so it can avoid duplicate "
            "search intent and build on existing content intelligently."
        ),
        "site":   cfg.get("site_base_url", "https://paulsellsproperties.com"),
        "author": cfg.get("author_name", "Paul Adams II"),

        "article_counts": {
            "published":  len(published),
            "scheduled":  len(scheduled),
            "backlog":    len(backlog.get("entries", [])),
            "watch_list": len(watch.get("entries", [])),
        },

        "published_articles":  published,
        "scheduled_articles":  scheduled,

        "backlog":    [e for e in backlog.get("entries", []) if e.get("status", "pending") not in ("dismissed",)],
        "watch_list": [e for e in watch.get("entries", []) if e.get("status", "active") not in ("dismissed", "expired")],

        "site_pages": SITE_PAGES,

        "taxonomy": {
            "article_types":           ARTICLE_TYPES,
            "categories":              CATEGORIES,
            "categories_in_use":       categories_in_use,
            "audience_taxonomy":       AUDIENCE_TAXONOMY,
            "audiences_in_use":        audiences_in_use,
            "content_types":           CONTENT_TYPES,
            "content_freshness_types": CONTENT_FRESHNESS_TYPES,
        },

        "editorial_rules_summary": {
            "em_dash_prohibition":   "HARD RULE: No em dash character (—, U+2014) anywhere. Use comma, semicolon, or colon instead.",
            "no_h1_in_body":         "body_html must NOT contain H1 tags. H1 is rendered from the title field.",
            "required_h2":           "body_html must contain at least one H2 heading.",
            "min_words":             900,
            "max_words":             2200,
            "article_count_per_batch": 3,
            "output_format":         "Produce one JSON package matching PACKAGE_SCHEMA.md. Do not produce articles separately.",
        },
    }

    output_path.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def main():
    args = sys.argv[1:]
    output_path = None

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_path = Path(args[idx + 1])
        else:
            print("  ✗ --output requires a path argument\n")
            sys.exit(1)

    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    print("\n  Generating editorial context...")
    written = build_context(output_path)
    print(f"  ✓ Written: {written}")
    print(f"\n  Paste the contents of this file into ChatGPT before beginning")
    print(f"  your weekly editorial research session.\n")


if __name__ == "__main__":
    main()
