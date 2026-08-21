"""
Site surface updater for the editorial automation system.

Rebuilds the homepage blog section, blog archive, sitemap, and RSS feed
from the canonical article registry (content-system/article-index.json).

ALL public surfaces are derived from a single source:
  article-index.json → publication filter → sorted newest-first
                      → homepage (newest 6 visible, rest hidden)
                      → blog archive (all published)
                      → sitemap (static pages + all published articles)
                      → RSS feed (all published articles)
"""

import html as html_lib
import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Sentinel markers (injected into HTML files) ───────────────────────────────
HOMEPAGE_GRID_START = "<!-- BEGIN:blog-grid -->"
HOMEPAGE_GRID_END   = "<!-- END:blog-grid -->"
HOMEPAGE_MORE_START = "<!-- BEGIN:blog-more -->"
HOMEPAGE_MORE_END   = "<!-- END:blog-more -->"
ARCHIVE_GRID_START  = "<!-- BEGIN:blog-archive -->"
ARCHIVE_GRID_END    = "<!-- END:blog-archive -->"

# ── Static sitemap pages ──────────────────────────────────────────────────────
# Tuples: (loc, changefreq, priority, lastmod_fixed_or_None)
# None → use today's date (pages that change whenever new articles are published)
_STATIC_SITEMAP_PAGES = [
    ("https://paulsellsproperties.com/",                              "weekly",  "1.0", None),
    ("https://paulsellsproperties.com/about.html",                   "monthly", "0.9", "2026-08-16"),
    ("https://paulsellsproperties.com/contact.html",                 "monthly", "0.8", "2026-08-16"),
    ("https://paulsellsproperties.com/property-search.html",         "daily",   "0.9", "2026-08-16"),
    ("https://paulsellsproperties.com/buying-selling-tips.html",     "monthly", "0.8", "2026-08-16"),
    ("https://paulsellsproperties.com/home-valuation.html",         "monthly", "0.8", "2026-08-16"),
    ("https://paulsellsproperties.com/blog/",                        "weekly",  "0.8", None),
    ("https://paulsellsproperties.com/neighborhoods/",               "monthly", "0.8", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/beverly-hills.html",   "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/bel-air.html",         "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/hollywood-hills.html", "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/santa-monica.html",    "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/venice.html",          "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/silver-lake.html",     "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/west-hollywood.html",  "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/los-feliz.html",       "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/studio-city.html",     "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/sherman-oaks.html",    "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/encino.html",          "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/highland-park.html",   "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/west-adams.html",      "monthly", "0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/pacific-palisades.html","monthly","0.7", "2026-08-16"),
    ("https://paulsellsproperties.com/neighborhoods/downtown-la.html",     "monthly", "0.7", "2026-08-16"),
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _la_now() -> datetime:
    return datetime.now(ZoneInfo("America/Los_Angeles"))


def _parse_dt(iso_str: str) -> datetime:
    """Parse an ISO 8601 string. Naive datetimes are assumed America/Los_Angeles."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    return dt


def _get_published_articles(article_index: list, now_la: datetime) -> list:
    """
    Return articles that are status='published' AND published_at <= now_la,
    sorted newest-first (by published_at, then scheduled_publish_at as fallback).
    Python's sort is stable, so same-timestamp articles preserve registry order.
    """
    eligible = []
    for a in article_index:
        if a.get("status") != "published":
            continue
        ts = a.get("published_at") or a.get("scheduled_publish_at")
        if not ts:
            continue
        try:
            if _parse_dt(ts) <= now_la:
                eligible.append(a)
        except (ValueError, TypeError):
            continue
    eligible.sort(
        key=lambda a: a.get("published_at") or a.get("scheduled_publish_at") or "",
        reverse=True,
    )
    return eligible


def _sort_key(article: dict) -> str:
    return article.get("published_at") or article.get("scheduled_publish_at") or ""


def _replace_sentinel(html: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = html.find(start_marker)
    end   = html.find(end_marker)
    if start == -1 or end == -1:
        raise ValueError(
            f"Sentinel markers not found in HTML.\n"
            f"  Looking for: {start_marker!r}\n"
            f"           and: {end_marker!r}"
        )
    return html[: start + len(start_marker)] + replacement + html[end:]


def _fmt_short(iso_str: str) -> str:
    """'Apr 28, 2026' — used on homepage cards."""
    try:
        return _parse_dt(iso_str).strftime("%b %-d, %Y")
    except (ValueError, TypeError):
        return iso_str


def _fmt_long(iso_str: str) -> str:
    """'April 28, 2026' — used in archive cards and RSS."""
    try:
        return _parse_dt(iso_str).strftime("%B %-d, %Y")
    except (ValueError, TypeError):
        return iso_str


def _fmt_rfc2822(iso_str: str) -> str:
    """RFC 2822 date for RSS pubDate."""
    try:
        dt = _parse_dt(iso_str)
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, TypeError):
        return datetime.now(ZoneInfo("UTC")).strftime("%a, %d %b %Y %H:%M:%S +0000")


# ── Card renderers ────────────────────────────────────────────────────────────

def _homepage_card_html(article: dict, hidden: bool = False) -> str:
    slug     = article["slug"]
    title    = html_lib.escape(article.get("title", ""))
    category = html_lib.escape(article.get("category", ""))
    excerpt  = html_lib.escape(article.get("excerpt", ""))
    ts       = article.get("published_at") or article.get("scheduled_publish_at", "")
    date_str = _fmt_short(ts) if ts else article.get("date_display", "")
    wrap_cls = "blog-card-wrap hidden" if hidden else "blog-card-wrap"

    return (
        f'      <div class="{wrap_cls}">\n'
        f'        <a href="blog/{slug}.html" class="blog-card">\n'
        f'          <div class="blog-card-body">\n'
        f'            <div class="blog-cat">{category}</div>\n'
        f'            <h3>{title}</h3>\n'
        f'            <p>{excerpt}</p>\n'
        f'            <div class="blog-meta">'
        f'<span>{date_str}</span>'
        f'<span class="blog-meta-dot">&middot;</span>'
        f'<span>Paul Adams II</span>'
        f'</div>\n'
        f'          </div>\n'
        f'        </a>\n'
        f'      </div>\n'
    )


def _archive_card_html(article: dict) -> str:
    slug     = article["slug"]
    title    = html_lib.escape(article.get("title", ""))
    category = html_lib.escape(article.get("category", ""))
    excerpt  = html_lib.escape(article.get("excerpt", ""))
    ts       = article.get("published_at") or article.get("scheduled_publish_at", "")
    date_str = _fmt_long(ts) if ts else article.get("date_display", "")

    return (
        f'\n      <a href="{slug}.html" class="blog-card">\n'
        f'        <div class="blog-card-body">\n'
        f'          <div class="blog-category">{category}</div>\n'
        f'          <h3>{title}</h3>\n'
        f'          <p>{excerpt}</p>\n'
        f'          <div class="blog-meta"><span>{date_str}</span></div>\n'
        f'        </div>\n'
        f'      </a>\n'
    )


# ── Public surface rebuilders ─────────────────────────────────────────────────

def update_homepage(article_index: list, homepage_path: Path,
                    now_la: datetime = None) -> int:
    """
    Rebuild the blog section of index.html from the registry.
    Replaces content between HOMEPAGE_GRID_START/END and HOMEPAGE_MORE_START/END sentinels.
    Returns the count of published articles rendered.
    """
    if now_la is None:
        now_la = _la_now()

    eligible = _get_published_articles(article_index, now_la)
    visible  = eligible[:6]
    overflow = eligible[6:]

    # Build grid content
    grid_html = "\n"
    for a in visible:
        grid_html += _homepage_card_html(a, hidden=False)
    for a in overflow:
        grid_html += _homepage_card_html(a, hidden=True)
    grid_html += "    "   # indent before closing </div>

    # Build show-more content
    if overflow:
        more_html = (
            '\n    <div class="blog-more-wrap">\n'
            '      <button class="btn btn-outline-dark" id="blogMoreBtn">\n'
            '        Show More Articles\n'
            '      </button>\n'
            '    </div>\n  '
        )
    else:
        more_html = (
            '\n    <div class="blog-more-wrap" style="display:none;">\n'
            '      <button class="btn btn-outline-dark" id="blogMoreBtn">\n'
            '        Show More Articles\n'
            '      </button>\n'
            '    </div>\n  '
        )

    html = homepage_path.read_text(encoding="utf-8")
    html = _replace_sentinel(html, HOMEPAGE_GRID_START, HOMEPAGE_GRID_END, grid_html)
    html = _replace_sentinel(html, HOMEPAGE_MORE_START, HOMEPAGE_MORE_END, more_html)
    homepage_path.write_text(html, encoding="utf-8")

    print(f"[site_updater] index.html updated: "
          f"{len(visible)} visible, {len(overflow)} overflow ({len(eligible)} total published)")
    return len(eligible)


def update_blog_archive(article_index: list, blog_index_path: Path,
                        now_la: datetime = None) -> int:
    """
    Full rebuild of blog/index.html archive from the registry.
    Replaces content between ARCHIVE_GRID_START/END sentinels.
    Returns the count of published articles rendered.
    """
    if now_la is None:
        now_la = _la_now()

    eligible = _get_published_articles(article_index, now_la)

    archive_html = ""
    for a in eligible:
        archive_html += _archive_card_html(a)
    archive_html += "\n    "  # indent before closing </div>

    html = blog_index_path.read_text(encoding="utf-8")
    html = _replace_sentinel(html, ARCHIVE_GRID_START, ARCHIVE_GRID_END, archive_html)
    blog_index_path.write_text(html, encoding="utf-8")

    print(f"[site_updater] blog/index.html rebuilt: {len(eligible)} articles")
    return len(eligible)


def update_sitemap_full(article_index: list, sitemap_path: Path,
                        cfg: dict, now_la: datetime = None) -> None:
    """
    Rebuild sitemap.xml from scratch: static pages + all published articles.
    """
    if now_la is None:
        now_la = _la_now()
    today = now_la.date().isoformat()

    published = _get_published_articles(article_index, now_la)
    base_url  = cfg.get("site_base_url", "https://paulsellsproperties.com")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             '',
             '  <!-- Core pages -->']

    for loc, changefreq, priority, fixed_lastmod in _STATIC_SITEMAP_PAGES:
        lastmod = fixed_lastmod if fixed_lastmod else today
        lines.append(f'  <url>')
        lines.append(f'    <loc>{loc}</loc>')
        lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append(f'    <changefreq>{changefreq}</changefreq>')
        lines.append(f'    <priority>{priority}</priority>')
        lines.append(f'  </url>')

    if published:
        lines.append('')
        lines.append('  <!-- Blog articles -->')
        for a in published:
            slug    = a["slug"]
            lastmod = a.get("date_iso", today)
            lines.append(f'  <url>')
            lines.append(f'    <loc>{base_url}/blog/{slug}.html</loc>')
            lines.append(f'    <lastmod>{lastmod}</lastmod>')
            lines.append(f'    <changefreq>monthly</changefreq>')
            lines.append(f'    <priority>0.7</priority>')
            lines.append(f'  </url>')

    lines.append('')
    lines.append('</urlset>')

    sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[site_updater] sitemap.xml rebuilt: "
          f"{len(_STATIC_SITEMAP_PAGES)} static + {len(published)} article URLs")


def update_rss_full(article_index: list, rss_path: Path,
                    cfg: dict, now_la: datetime = None) -> None:
    """
    Rebuild feed.xml from scratch using all published articles, newest-first.
    """
    if now_la is None:
        now_la = _la_now()

    published   = _get_published_articles(article_index, now_la)
    base_url    = cfg.get("site_base_url", "https://paulsellsproperties.com")
    author_name = cfg.get("author_name", "Paul Adams II")
    og_image    = cfg.get("default_og_image", f"{base_url}/assets/images/paul-hero.png")
    build_date  = _fmt_rfc2822(now_la.isoformat())

    items = []
    for a in published:
        slug    = a["slug"]
        url     = f"{base_url}/blog/{slug}.html"
        title   = html_lib.escape(a.get("title", ""))
        desc    = html_lib.escape(a.get("excerpt", a.get("primary_keyword", "")))
        cat     = html_lib.escape(a.get("category", ""))
        pub_ts  = a.get("published_at") or a.get("scheduled_publish_at", "")
        pub_date = _fmt_rfc2822(pub_ts) if pub_ts else build_date
        items.append(
            f"    <item>\n"
            f"      <title>{title}</title>\n"
            f"      <link>{url}</link>\n"
            f"      <description>{desc}</description>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"      <guid isPermaLink=\"true\">{url}</guid>\n"
            f"      <category>{cat}</category>\n"
            f"    </item>"
        )

    xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        f'  <channel>\n'
        f'    <title>{author_name} | Los Angeles Real Estate Insights</title>\n'
        f'    <link>{base_url}/</link>\n'
        f'    <description>Real estate strategy, market analysis, and Los Angeles neighborhood '
        f'insights from {author_name}, Coldwell Banker Realty Beverly Hills.</description>\n'
        f'    <language>en-us</language>\n'
        f'    <lastBuildDate>{build_date}</lastBuildDate>\n'
        f'    <atom:link href="{base_url}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        f'    <image>\n'
        f'      <url>{og_image}</url>\n'
        f'      <title>{author_name} | Los Angeles Real Estate</title>\n'
        f'      <link>{base_url}/</link>\n'
        f'    </image>\n'
        + "\n".join(items) + "\n"
        f'  </channel>\n'
        f'</rss>'
    )

    rss_path.write_text(xml, encoding="utf-8")
    print(f"[site_updater] feed.xml rebuilt: {len(published)} items")


# ── Article registry update ───────────────────────────────────────────────────

def update_article_index(articles: list, index_path: Path) -> None:
    """
    Add newly approved articles to article-index.json.
    Articles should already carry all required fields (status, scheduled_publish_at, etc.)
    before being passed here. Duplicate slugs are skipped with a warning.
    """
    existing: list = []
    if index_path.exists():
        with open(index_path) as f:
            existing = json.load(f)

    existing_slugs = {a["slug"] for a in existing}

    for article in articles:
        slug = article["slug"]
        if slug in existing_slugs:
            print(f"[site_updater] WARNING: slug '{slug}' already in index — skipping")
            continue

        base_url = article.get("site_base_url", "https://paulsellsproperties.com")
        entry = {
            "slug":                 slug,
            "title":                article.get("headline", ""),
            "excerpt":              article.get("excerpt", article.get("meta_description", "")),
            "url":                  f"{base_url}/blog/{slug}.html",
            "status":               article.get("status", "approved"),
            "scheduled_publish_at": article.get("scheduled_publish_at"),
            "published_at":         article.get("published_at"),
            "date_iso":             article.get("date_iso", ""),
            "date_display":         article.get("date_display", ""),
            "category":             article.get("category", ""),
            "author":               article.get("author_name", "Paul Adams II"),
            "article_type":         article.get("article_type", "B"),
            "primary_topic":        article.get("topic_rationale", ""),
            "primary_keyword":      article.get("primary_keyword", ""),
            "secondary_topics":     article.get("secondary_keywords", []),
            "search_intent":        article.get("search_intent", ""),
            "geographic_focus":     article.get("geographic_focus", "Los Angeles"),
            "audience":             article.get("audience", []),
            "content_type":         article.get("content_type", ""),
            "evergreen":            article.get("evergreen", True),
            "pillar":               article.get("pillar"),
            "tags":                 article.get("tags", []),
            "internal_links":       [
                lnk.get("url", "").split("/")[-1].replace(".html", "")
                for lnk in article.get("internal_links_used", [])
            ],
            "related_articles":     article.get("related_articles", []),
            "review_after":         article.get("review_after"),
            "last_reviewed":        article.get("date_iso", ""),
            "word_count_approx":    article.get("word_count_estimate", 0),
        }
        existing.append(entry)
        existing_slugs.add(slug)
        print(f"[site_updater] Added to index: {slug} (status={entry['status']})")

    with open(index_path, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"[site_updater] article-index.json saved ({len(existing)} total articles)")
