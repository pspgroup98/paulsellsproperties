"""
Article generation via OpenAI Chat Completions.

Sends the editorial guidelines and topic brief to the writing model and returns
a structured article dict ready for validation and HTML assembly.
"""
import json
import re
import unicodedata


EM_DASH = "—"

KNOWN_INTERNAL_PAGES = {
    "property-search": "../property-search.html",
    "buying-selling-tips": "../buying-selling-tips.html",
    "about": "../about.html",
    "contact": "../contact.html",
    "home-valuation": "../home-valuation.html",
    "neighborhoods": "../neighborhoods/index.html",
    "beverly-hills": "../neighborhoods/beverly-hills.html",
    "bel-air": "../neighborhoods/bel-air.html",
    "hollywood-hills": "../neighborhoods/hollywood-hills.html",
    "santa-monica": "../neighborhoods/santa-monica.html",
    "silver-lake": "../neighborhoods/silver-lake.html",
    "venice": "../neighborhoods/venice.html",
    "blog": "index.html",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    # Trim to a reasonable slug length (max 70 chars, break at word boundary)
    if len(text) > 70:
        text = text[:70].rsplit("-", 1)[0]
    return text


TYPE_LABELS = {
    "A": "Timely/Market Intelligence",
    "B": "Evergreen/Consumer Education",
    "C": "Authority/Investment",
}


def build_writing_prompt(topic: dict, editorial_guidelines: str, existing_articles: list, cfg: dict) -> str:
    related = [
        f"- {a['title']} (/{cfg['blog_path']}/{a['slug']}.html)"
        for a in existing_articles
        if a.get("category") == topic.get("category") or
           any(t in a.get("tags", []) for t in topic.get("tags_hint", []))
    ][:4]
    related_str = "\n".join(related) if related else "None identified"

    type_label = TYPE_LABELS.get(topic.get("article_type", "B"), "")

    return f"""You are writing an article for paulsellsproperties.com, the website of Paul Adams II, a Los Angeles real estate agent at Coldwell Banker Realty Beverly Hills.

EDITORIAL GUIDELINES (follow these strictly):
{editorial_guidelines}

TOPIC ASSIGNMENT:
- Topic: {topic.get('topic')}
- Article type: {topic.get('article_type', 'B')} ({type_label})
- Category: {topic.get('category')}
- Primary keyword: {topic.get('primary_keyword', '')}
- Rationale: {topic.get('rationale', '')}
- Key sources suggested: {', '.join(topic.get('key_sources', []))}

POTENTIALLY RELEVANT EXISTING ARTICLES (link to these contextually where natural):
{related_str}

SITE PAGES AVAILABLE FOR INTERNAL LINKING:
- Property search: ../property-search.html
- Buying and selling tips: ../buying-selling-tips.html
- Neighborhoods landing: ../neighborhoods/index.html
- Contact: ../contact.html
- Home valuation: ../home-valuation.html
- About Paul: ../about.html

REQUIREMENTS:
1. Write a complete, high-quality article that genuinely serves Los Angeles real estate buyers, sellers, landlords, or investors.
2. The body_html field must contain ONLY the article body content (paragraphs, headings, lists, blockquotes, the FAQ section, and the CTA box). Do NOT include an H1 — the page template renders the headline separately.
3. Use H2 for main sections, H3 for sub-points. Do not over-structure short content with excessive headings.
4. Include an FAQ section (h2 "Frequently Asked Questions" with h3/p pairs) unless the topic is unsuitable for FAQ format.
5. End with a div.post-cta-box — see the structure example below.
6. DO NOT use the em dash character (—, Unicode U+2014) anywhere. Not in headlines, not in body, not in meta. Use commas, colons, semicolons, or rewrite the sentence instead.
7. Do not fabricate statistics, laws, quotes, transaction data, or claims about Paul's personal experience.
8. Avoid all phrases listed as prohibited in the guidelines.
9. Internal links: use <a href="[relative-url]"> with descriptive anchor text. Link naturally, not forcefully. Report which links you used.
10. Meta description: 130-155 characters, does not repeat the headline verbatim.
11. Minimum article body: 900 words of substantive content.
12. Suggest 4-8 topic tags for the article index.

CTA BOX STRUCTURE (must appear at the end of body_html):
<div class="post-cta-box">
  <h3>[Specific CTA headline related to this article's topic]</h3>
  <p>[1-2 sentences connecting what the reader just learned to what Paul can help them do]</p>
  <div class="btn-group">
    <a href="../contact.html" class="btn btn-primary">Get in Touch</a>
    <a href="#" class="btn btn-outline" onclick="Calendly.initPopupWidget({{url:'https://calendly.com/adams2paul'}});return false;">Start a Conversation</a>
  </div>
</div>

Return ONLY valid JSON in this exact structure (no markdown fence, no extra text):
{{
  "headline": "The article headline — will be rendered as H1 on the page",
  "suggested_slug": "url-safe-slug-for-the-article",
  "meta_description": "130-155 character meta description",
  "category": "Category name",
  "article_type": "A|B|C",
  "primary_keyword": "main search query",
  "secondary_keywords": ["keyword 2", "keyword 3"],
  "tags": ["tag1", "tag2", "tag3"],
  "audience": ["buyers|sellers|investors|landlords|homeowners"],
  "evergreen": true,
  "geographic_focus": "Los Angeles",
  "body_html": "<p>Full article body HTML here...</p>",
  "internal_links_used": [
    {{"anchor_text": "the anchor", "url": "../path/to/page.html"}}
  ],
  "key_sources": ["Source 1", "Source 2"],
  "word_count_estimate": 0,
  "topic_rationale": "Why this topic was selected this week"
}}"""


def generate_article(client, topic: dict, editorial_guidelines: str, existing_articles: list, cfg: dict) -> dict:
    """Call OpenAI to generate one article. Returns the article dict."""
    model = cfg.get("writing_model", "gpt-4o")
    prompt = build_writing_prompt(topic, editorial_guidelines, existing_articles, cfg)

    print(f"[article_generator] Writing '{topic.get('suggested_headline', topic.get('topic'))}' with {model}...")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.6,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content
    try:
        article = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse article JSON: {e}\nRaw: {raw[:300]}")

    # Finalize slug
    raw_slug = article.get("suggested_slug", "")
    article["slug"] = slugify(raw_slug or article.get("headline", "article"))

    # Ensure article_type and category are set
    article.setdefault("article_type", topic.get("article_type", "B"))
    article.setdefault("category", topic.get("category", "Buyer's Guide"))
    article.setdefault("geographic_focus", "Los Angeles")
    article.setdefault("key_sources", topic.get("key_sources", []))
    article.setdefault("topic_rationale", topic.get("rationale", ""))

    return article


def request_em_dash_correction(client, article: dict, editorial_guidelines: str, cfg: dict) -> dict:
    """Request a corrected version of an article that contains em dashes."""
    model = cfg.get("writing_model", "gpt-4o")
    print(f"[article_generator] Requesting em dash correction for '{article.get('headline', '')}'...")

    body = article.get("body_html", "")
    headline = article.get("headline", "")
    desc = article.get("meta_description", "")

    correction_prompt = f"""The following article content contains em dash characters (—, Unicode U+2014).
This is strictly prohibited. Replace every em dash with a comma, semicolon, colon, or rewrite the phrase.
Do not use any other Unicode dash variants either. Return ONLY the corrected JSON fields.

HEADLINE TO CORRECT: {headline}
META DESCRIPTION TO CORRECT: {desc}
BODY HTML TO CORRECT:
{body}

Return valid JSON with these exact fields and nothing else:
{{
  "headline": "corrected headline",
  "meta_description": "corrected meta description",
  "body_html": "corrected body HTML"
}}"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": correction_prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=4000,
    )
    raw = response.choices[0].message.content
    try:
        corrections = json.loads(raw)
        article["headline"] = corrections.get("headline", headline)
        article["meta_description"] = corrections.get("meta_description", desc)
        article["body_html"] = corrections.get("body_html", body)
    except json.JSONDecodeError:
        pass  # validator will catch remaining issues

    return article
