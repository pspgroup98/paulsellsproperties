"""
Updates blog/index.html, sitemap.xml, feed.xml, and content-system/article-index.json
for each newly generated article.
"""
import json
import re
from datetime import date, timezone, datetime
from pathlib import Path
import html as html_lib


def _format_display_date(iso_date: str) -> str:
    try:
        d = date.fromisoformat(iso_date)
        return d.strftime("%B %-d, %Y")
    except Exception:
        return iso_date


# ── Blog index ────────────────────────────────────────────────────────────────

def _blog_card_html(article: dict) -> str:
    """Generate a blog-card element for blog/index.html."""
    slug = article["slug"]
    title = html_lib.escape(article["headline"])
    category = html_lib.escape(article["category"])
    date_display = article.get("date_display", _format_display_date(article.get("date_iso", "")))
    # First sentence of body as teaser, stripped of HTML tags
    body = article.get("body_html", "")
    plain = re.sub(r'<[^>]+>', '', body)
    first_para = plain.strip().split('\n')[0].strip()
    teaser = (first_para[:180] + '...') if len(first_para) > 180 else first_para

    return (
        f'\n      <a href="{slug}.html" class="blog-card">\n'
        f'        <div class="blog-card-body">\n'
        f'          <div class="blog-category">{category}</div>\n'
        f'          <h3>{title}</h3>\n'
        f'          <p>{html_lib.escape(teaser)}</p>\n'
        f'          <div class="blog-meta"><span>{date_display}</span></div>\n'
        f'        </div>\n'
        f'      </a>'
    )


def update_blog_index(articles: list, blog_index_path: Path) -> None:
    html = blog_index_path.read_text(encoding="utf-8")
    grid_marker = '<div class="blog-grid">'
    if grid_marker not in html:
        raise ValueError("Could not find .blog-grid in blog/index.html")

    # Insert all new cards immediately after the grid opening tag (newest first)
    insert_pos = html.index(grid_marker) + len(grid_marker)
    cards_html = "".join(_blog_card_html(a) for a in articles)
    html = html[:insert_pos] + cards_html + html[insert_pos:]
    blog_index_path.write_text(html, encoding="utf-8")
    print(f"[site_updater] blog/index.html updated with {len(articles)} new card(s)")


# ── Sitemap ───────────────────────────────────────────────────────────────────

def _sitemap_url(article: dict, cfg: dict) -> str:
    base_url = cfg.get("site_base_url", "https://paulsellsproperties.com")
    slug = article["slug"]
    date_iso = article.get("date_iso", date.today().isoformat())
    return (
        f"  <url>\n"
        f"    <loc>{base_url}/blog/{slug}.html</loc>\n"
        f"    <lastmod>{date_iso}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.7</priority>\n"
        f"  </url>"
    )


def update_sitemap(articles: list, sitemap_path: Path, cfg: dict) -> None:
    xml = sitemap_path.read_text(encoding="utf-8")
    closing_tag = "</urlset>"
    if closing_tag not in xml:
        raise ValueError("Could not find </urlset> in sitemap.xml")

    new_entries = "\n".join(_sitemap_url(a, cfg) for a in articles) + "\n"
    xml = xml.replace(closing_tag, new_entries + closing_tag)
    sitemap_path.write_text(xml, encoding="utf-8")
    print(f"[site_updater] sitemap.xml updated with {len(articles)} new URL(s)")


# ── RSS feed ──────────────────────────────────────────────────────────────────

def _rss_pub_date(iso_date: str) -> str:
    try:
        d = date.fromisoformat(iso_date)
        dt = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _rss_item(article: dict, cfg: dict) -> str:
    base_url = cfg.get("site_base_url", "https://paulsellsproperties.com")
    slug = article["slug"]
    url = f"{base_url}/blog/{slug}.html"
    title = html_lib.escape(article["headline"])
    desc = html_lib.escape(article.get("meta_description", ""))
    category = html_lib.escape(article["category"])
    pub_date = _rss_pub_date(article.get("date_iso", ""))
    return (
        f"    <item>\n"
        f"      <title>{title}</title>\n"
        f"      <link>{url}</link>\n"
        f"      <description>{desc}</description>\n"
        f"      <pubDate>{pub_date}</pubDate>\n"
        f"      <guid isPermaLink=\"true\">{url}</guid>\n"
        f"      <category>{category}</category>\n"
        f"    </item>"
    )


def create_or_update_rss(articles: list, rss_path: Path, cfg: dict, all_articles: list = None) -> None:
    base_url = cfg.get("site_base_url", "https://paulsellsproperties.com")
    author_name = cfg.get("author_name", "Paul Adams II")

    if rss_path.exists():
        xml = rss_path.read_text(encoding="utf-8")
        closing = "</channel>"
        if closing not in xml:
            raise ValueError("Could not find </channel> in feed.xml")
        new_items = "\n".join(_rss_item(a, cfg) for a in articles) + "\n"
        # Update lastBuildDate
        xml = re.sub(
            r'<lastBuildDate>[^<]+</lastBuildDate>',
            f'<lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>',
            xml
        )
        xml = xml.replace(closing, new_items + "  " + closing)
    else:
        # Build from scratch with all known articles
        source_articles = list(articles)
        if all_articles:
            known_slugs = {a["slug"] for a in articles}
            extras = [a for a in all_articles if a["slug"] not in known_slugs]
            # Most recent first
            extras.sort(key=lambda x: x.get("date_iso", ""), reverse=True)
            source_articles = list(articles) + extras

        items = "\n".join(_rss_item(a, cfg) for a in source_articles)
        now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{author_name} | Los Angeles Real Estate Insights</title>
    <link>{base_url}/</link>
    <description>Real estate strategy, market analysis, and Los Angeles neighborhood insights from {author_name}, Coldwell Banker Realty Beverly Hills.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{base_url}/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>{cfg.get('default_og_image', '')}</url>
      <title>{author_name} | Los Angeles Real Estate</title>
      <link>{base_url}/</link>
    </image>
{items}
  </channel>
</rss>"""

    rss_path.write_text(xml, encoding="utf-8")
    print(f"[site_updater] feed.xml updated with {len(articles)} new item(s)")


# ── Article index ─────────────────────────────────────────────────────────────

def update_article_index(articles: list, index_path: Path) -> None:
    existing = []
    if index_path.exists():
        with open(index_path) as f:
            existing = json.load(f)

    existing_slugs = {a["slug"] for a in existing}
    for article in articles:
        if article["slug"] in existing_slugs:
            print(f"[site_updater] WARNING: slug '{article['slug']}' already in index — skipping")
            continue
        entry = {
            "slug": article["slug"],
            "title": article["headline"],
            "url": f"{article.get('site_base_url', 'https://paulsellsproperties.com')}/blog/{article['slug']}.html",
            "date_iso": article.get("date_iso", ""),
            "date_display": article.get("date_display", ""),
            "category": article.get("category", ""),
            "article_type": article.get("article_type", "B"),
            "primary_topic": article.get("topic_rationale", ""),
            "primary_keyword": article.get("primary_keyword", ""),
            "secondary_topics": article.get("secondary_keywords", []),
            "geographic_focus": article.get("geographic_focus", "Los Angeles"),
            "audience": article.get("audience", []),
            "evergreen": article.get("evergreen", True),
            "tags": article.get("tags", []),
            "internal_links": [lnk.get("url", "").split("/")[-1].replace(".html", "")
                               for lnk in article.get("internal_links_used", [])],
            "word_count_approx": article.get("word_count_estimate", 0),
        }
        existing.append(entry)
        existing_slugs.add(article["slug"])

    with open(index_path, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"[site_updater] article-index.json updated ({len(existing)} total articles)")
