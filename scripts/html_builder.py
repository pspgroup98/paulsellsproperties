"""
HTML page builder for generated articles.
Renders the complete article HTML from structured article data.
Does NOT read or modify any existing files.
"""
import html as html_lib
import json
from datetime import date, datetime
from pathlib import Path

_PARTIALS_DIR = Path(__file__).resolve().parent.parent / '_partials'


def build_json_ld(article: dict, cfg: dict) -> str:
    slug = article["slug"]
    base_url = cfg.get("site_base_url", "https://paulsellsproperties.com")
    article_url = f"{base_url}/blog/{slug}"
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": f"{article_url}#post",
                "headline": article["headline"],
                "description": article["meta_description"],
                "url": article_url,
                "datePublished": article["date_iso"],
                "author": {
                    "@type": "Person",
                    "@id": cfg.get("author_id", "https://paulsellsproperties.com/#paul"),
                    "name": cfg.get("author_name", "Paul Adams II"),
                    "url": cfg.get("author_url", "https://paulsellsproperties.com/about"),
                },
                "publisher": {"@id": cfg.get("agent_id", "https://paulsellsproperties.com/#agent")},
                "isPartOf": {"@id": cfg.get("website_id", "https://paulsellsproperties.com/#website")},
                "image": cfg.get("default_og_image", "https://paulsellsproperties.com/assets/images/paul-hero.png"),
                "inLanguage": "en-US",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base_url}/"},
                    {"@type": "ListItem", "position": 2, "name": "Real Estate Insights", "item": f"{base_url}/blog/"},
                    {"@type": "ListItem", "position": 3, "name": article["headline"], "item": article_url},
                ],
            },
        ],
    }
    return json.dumps(data, separators=(",", ":"))


def format_display_date(iso_date: str) -> str:
    try:
        d = date.fromisoformat(iso_date)
        return d.strftime("%B %-d, %Y")
    except Exception:
        return iso_date


def build_article_html(article: dict, cfg: dict) -> str:
    slug = article["slug"]
    base_url = cfg.get("site_base_url", "https://paulsellsproperties.com")
    article_url = f"{base_url}/blog/{slug}"
    og_image = cfg.get("default_og_image", "https://paulsellsproperties.com/assets/images/paul-hero.png")
    headline_esc = html_lib.escape(article["headline"])
    seo_title_esc = html_lib.escape(article.get("seo_title") or article["headline"])
    meta_esc = html_lib.escape(article["meta_description"])
    date_display = article.get("date_display", format_display_date(article.get("date_iso", "")))
    category_esc = html_lib.escape(article["category"])
    json_ld = build_json_ld(article, cfg)
    nav_partial = (_PARTIALS_DIR / 'nav.html').read_text(encoding='utf-8').rstrip('\n')
    footer_partial = (_PARTIALS_DIR / 'footer.html').read_text(encoding='utf-8').rstrip('\n')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{seo_title_esc}</title>
  <meta name="description" content="{meta_esc}">
  <link rel="canonical" href="{article_url}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{seo_title_esc}">
  <meta property="og:description" content="{meta_esc}">
  <meta property="og:url" content="{article_url}">
  <meta property="og:site_name" content="Paul Adams II">
  <meta property="og:image" content="{og_image}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{seo_title_esc}">
  <meta name="twitter:description" content="{meta_esc}">
  <meta name="twitter:image" content="{og_image}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <script type="application/ld+json">
  {json_ld}
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/styles.css">
  <link rel="stylesheet" href="../assets/css/design-tokens.css">
  <link rel="stylesheet" href="../assets/css/redesign.css">
  <!-- Analytics: Calendly is loaded on demand by PSP.openCalendly() — no eager load -->
  <script src="../assets/js/analytics.js" defer></script>
</head>
<body>

<!-- NAV -->
{nav_partial}

<!-- POST HEADER -->
<div class="post-header">
  <div class="container">
    <span class="post-category-tag">{category_esc}</span>
    <h1>{headline_esc}</h1>
    <div class="post-header-meta">
      <span>By Paul Adams II</span>
      <span>&middot;</span>
      <span>Los Angeles Real Estate Advisor</span>
      <span>&middot;</span>
      <span>{date_display}</span>
    </div>
  </div>
</div>

<!-- POST CONTENT -->
<article class="post-content">

{article['body_html']}

</article>

<!-- RELATED ARTICLES -->
<section class="post-more"
         data-slug="{slug}"
         data-article-slug="{slug}"
         data-article-category="{category_esc}"
         data-article-type="{article.get('article_type', '')}">
  <div class="container">
    <div class="post-more-header">
      <span class="post-more-label">Related Articles</span>
      <a href="/blog/" class="post-more-view-all">View All Insights &rarr;</a>
    </div>
    <div class="post-more-grid" id="relatedArticlesGrid">
      <!-- populated by assets/js/related-articles.js -->
    </div>
  </div>
</section>

<!-- FOOTER -->
{footer_partial}

<script src="../assets/js/nav.js" defer></script>
<script src="../assets/js/related-articles.js"></script>
</body>
</html>"""
