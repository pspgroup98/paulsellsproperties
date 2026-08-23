"""
HTML page builder for generated articles.
Renders the complete article HTML from structured article data.
Does NOT read or modify any existing files.
"""
import html as html_lib
import json
from datetime import date, datetime


# ── Footer (shared across all blog articles) ─────────────────────────────────
FOOTER_HTML = """<footer class="footer">
  <div class="footer-main">
    <div class="container">
      <div class="footer-grid">
        <div>
          <div class="footer-logo-wrap">
            <a href="../index.html" class="logo-mark">
              <span class="logo-name">Paul Adams II</span>
              <span class="logo-rule"></span>
              <span class="logo-sub">Los Angeles Real Estate</span>
            </a>
          </div>
          <p class="footer-tagline">Third-generation real estate advisor focused on strategy, clarity, and execution across Los Angeles.</p>
          <div class="footer-social">
            <a href="https://www.instagram.com/paulsellsproperties/" class="social-btn" target="_blank" rel="noopener" aria-label="Instagram"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg></a>
            <a href="https://www.facebook.com/profile.php?id=61580108736092" class="social-btn" target="_blank" rel="noopener" aria-label="Facebook"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg></a>
            <a href="https://share.google/EG2aS8iUzQFJ3ECnX" class="social-btn" target="_blank" rel="noopener" aria-label="Google Business Profile"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg></a>
          </div>
        </div>
        <div>
          <div class="footer-col-title">Navigate</div>
          <ul class="footer-links">
            <li><a href="../index.html">Home</a></li>
            <li><a href="../property-search.html">Property Search</a></li>
            <li><a href="../buying-selling-tips.html">Buying &amp; Selling</a></li>
            <li><a href="../about.html">About Me</a></li>
            <li><a href="../blog/index.html">Blog</a></li>
            <li><a href="../home-valuation.html">Home Valuation</a></li>
          </ul>
        </div>
        <div>
          <div class="footer-col-title">Neighborhoods</div>
          <ul class="footer-links">
            <li><a href="../neighborhoods/beverly-hills.html">Beverly Hills</a></li>
            <li><a href="../neighborhoods/bel-air.html">Bel Air</a></li>
            <li><a href="../neighborhoods/hollywood-hills.html">Hollywood Hills</a></li>
            <li><a href="../neighborhoods/santa-monica.html">Santa Monica</a></li>
            <li><a href="../neighborhoods/venice.html">Venice</a></li>
            <li><a href="../neighborhoods/silver-lake.html">Silver Lake</a></li>
          </ul>
        </div>
        <div>
          <div class="footer-col-title">Contact</div>
          <div class="footer-contact-block">
            <div class="footer-contact-lbl">Email</div>
            <div class="footer-contact-val"><a href="mailto:Paul.Adams@CBRealty.com">Paul.Adams@CBRealty.com</a></div>
          </div>
          <div class="footer-contact-block">
            <div class="footer-contact-lbl">Phone</div>
            <div class="footer-contact-val"><a href="tel:+13019066252">301-906-6252</a></div>
          </div>
          <div class="footer-contact-block">
            <div class="footer-contact-lbl">Office</div>
            <div class="footer-contact-val"><a href="https://www.google.com/maps/dir/?api=1&destination=301+N+Canon+Dr+Ste+E,+Beverly+Hills,+CA+90210" target="_blank" rel="noopener" style="color:inherit;">301 N Canon Dr Ste E<br>Beverly Hills, CA 90210</a></div>
          </div>
          <div class="footer-dre">CA DRE# 02232552</div>
        </div>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <div class="container">
      <div class="footer-bottom-inner">
        <p class="footer-legal">Paul Adams II | CA DRE# 02232552 | Coldwell Banker Residential Brokerage Company | CA DRE# 00616212 | &copy;2026 Coldwell Banker. All Rights Reserved. The Coldwell Banker&reg; System fully supports the principles of the Fair Housing Act and the Equal Opportunity Act.</p>
        <div class="footer-bottom-links">
          <a href="../terms.html">Terms</a>
          <a href="../privacy.html">Privacy</a>
          <a href="https://www.hud.gov/program_offices/fair_housing_equal_opp/fair_housing_act_overview" target="_blank" rel="noopener">Fair Housing</a>
        </div>
      </div>
    </div>
  </div>
</footer>"""

NAV_HTML = """<nav class="nav scrolled">
  <div class="nav-inner">
    <a href="../index.html" class="logo-mark"><span class="logo-name">Paul Adams II</span><span class="logo-rule"></span><span class="logo-sub">Los Angeles Real Estate</span></a>
    <ul class="nav-links">
      <li class="nav-item"><a href="../index.html">Home</a></li>
      <li class="nav-item"><span>Properties &#9662;</span>
        <div class="nav-dropdown-menu">
          <a href="../property-search.html">Property Search</a>
        </div>
      </li>
      <li class="nav-item"><span>Buying &amp; Selling &#9662;</span>
        <div class="nav-dropdown-menu">
          <a href="../buying-selling-tips.html">Buying &amp; Selling Tips</a>
        </div>
      </li>
      <li class="nav-item"><span>About Me &#9662;</span>
        <div class="nav-dropdown-menu">
          <a href="../about.html">My Bio</a>
          <a href="../contact.html">Contact Me</a>
        </div>
      </li>
      <li class="nav-item"><span>Neighborhoods &#9662;</span>
        <div class="nav-dropdown-menu">
          <a href="../neighborhoods/index.html">All Neighborhoods</a>
          <a href="../neighborhoods/beverly-hills.html">Beverly Hills</a>
          <a href="../neighborhoods/bel-air.html">Bel Air</a>
          <a href="../neighborhoods/hollywood-hills.html">Hollywood Hills</a>
          <a href="../neighborhoods/santa-monica.html">Santa Monica</a>
          <a href="../neighborhoods/silver-lake.html">Silver Lake</a>
          <a href="../neighborhoods/venice.html">Venice</a>
        </div>
      </li>
      <li class="nav-item"><a href="index.html">Blog</a></li>
      <li class="nav-item"><a href="../home-valuation.html">Custom Home Valuation</a></li>
    </ul>
    <div class="nav-right">
      <a href="#" class="btn btn-gold btn-sm"
         onclick="PSP.openCalendly('https://calendly.com/adams2paul');return false;">
        Start a Conversation
      </a>
    </div>
    <button class="nav-toggle" id="navToggle"><span></span><span></span><span></span></button>
  </div>
</nav>
<div class="nav-mobile" id="navMobile">
  <a href="../index.html">Home</a>
  <a href="../property-search.html" class="mobile-sub">Property Search</a>
  <a href="../buying-selling-tips.html">Buying &amp; Selling Tips</a>
  <a href="../about.html">My Bio</a>
  <a href="../contact.html">Contact Me</a>
  <a href="index.html">Blog</a>
  <a href="../neighborhoods/index.html">Neighborhoods</a>
  <a href="../home-valuation.html">Home Valuation</a>
</div>"""


def build_json_ld(article: dict, cfg: dict) -> str:
    slug = article["slug"]
    base_url = cfg.get("site_base_url", "https://paulsellsproperties.com")
    article_url = f"{base_url}/blog/{slug}.html"
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
                    "url": cfg.get("author_url", "https://paulsellsproperties.com/about.html"),
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
    article_url = f"{base_url}/blog/{slug}.html"
    og_image = cfg.get("default_og_image", "https://paulsellsproperties.com/assets/images/paul-hero.png")
    headline_esc = html_lib.escape(article["headline"])
    meta_esc = html_lib.escape(article["meta_description"])
    date_display = article.get("date_display", format_display_date(article.get("date_iso", "")))
    category_esc = html_lib.escape(article["category"])
    json_ld = build_json_ld(article, cfg)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{headline_esc} | Paul Adams II</title>
  <meta name="description" content="{meta_esc}">
  <link rel="canonical" href="{article_url}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{headline_esc} | Paul Adams II">
  <meta property="og:description" content="{meta_esc}">
  <meta property="og:url" content="{article_url}">
  <meta property="og:site_name" content="Paul Adams II">
  <meta property="og:image" content="{og_image}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{headline_esc} | Paul Adams II">
  <meta name="twitter:description" content="{meta_esc}">
  <meta name="twitter:image" content="{og_image}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <script type="application/ld+json">
  {json_ld}
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/styles.css">
  <!-- Analytics: Calendly is loaded on demand by PSP.openCalendly() — no eager load -->
  <script src="../assets/js/analytics.js" defer></script>
</head>
<body>

<!-- NAV -->
{NAV_HTML}

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
      <a href="index.html" class="post-more-view-all">View All Insights &rarr;</a>
    </div>
    <div class="post-more-grid" id="relatedArticlesGrid">
      <!-- populated by assets/js/related-articles.js -->
    </div>
  </div>
</section>

<!-- FOOTER -->
{FOOTER_HTML}

<script>
  document.getElementById('navToggle').addEventListener('click', () => {{
    document.getElementById('navMobile').classList.toggle('open');
  }});
</script>
<script src="../assets/js/related-articles.js"></script>
</body>
</html>"""
