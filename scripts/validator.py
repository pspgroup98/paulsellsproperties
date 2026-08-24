"""Article validation: em dash prohibition, quality checks, structural checks.

Phase 3 additions:
  scan_fields_for_em_dashes()  — per-field em dash scan with exact position reporting
  scan_for_other_dashes()      — en dash and other Unicode dash variant warnings
  check_source_completeness()  — warns when news/regulatory/market_data has no sources
  check_search_intent_overlap() — detects search intent overlap against existing registry
"""
import difflib
import re
from dataclasses import dataclass, field
from typing import Optional


EM_DASH = "—"   # — Unicode em dash (U+2014) — hard failure

# Other Unicode dash variants that may be silently substituted by editors.
# These are warnings, not hard failures.
EN_DASH       = "–"   # –
HORIZONTAL_BAR = "―"  # ―
FIGURE_DASH   = "‒"   # ‒
OTHER_DASH_CHARS = {EN_DASH: "en dash (U+2013)", HORIZONTAL_BAR: "horizontal bar (U+2015)", FIGURE_DASH: "figure dash (U+2012)"}

# Content types that require sources when making factual claims.
SOURCES_REQUIRED_TYPES = {"news", "regulatory", "market_data", "legal-regulatory", "market-insight", "market-analysis"}

# Phrases that signal generic AI writing — reported as warnings, not hard failures
QUALITY_PHRASES = [
    "in today's market",
    "navigating the",
    "whether you're",
    "whether you are",
    "dream home",
    "ever-evolving",
    "vibrant",
    "boasts",
    "it's important to note",
    "it is important to note",
    "in conclusion",
    "to summarize",
    "this article will",
    "without further ado",
    "at the end of the day",
    "game changer",
    "game-changer",
    "invaluable",
    "holistic approach",
    "best practices",
]


@dataclass
class ValidationResult:
    passed: bool
    em_dash_fail: bool = False
    em_dash_positions: list = field(default_factory=list)
    quality_warnings: list = field(default_factory=list)
    structural_warnings: list = field(default_factory=list)
    structural_errors: list = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        if self.em_dash_fail:
            lines.append(f"FAIL — em dash found at positions: {self.em_dash_positions[:5]}")
        else:
            lines.append("PASS — no em dash")
        if self.structural_errors:
            lines.append("STRUCTURAL ERRORS: " + "; ".join(self.structural_errors))
        if self.quality_warnings:
            lines.append("QUALITY WARNINGS: " + "; ".join(self.quality_warnings))
        if self.structural_warnings:
            lines.append("STRUCTURAL WARNINGS: " + "; ".join(self.structural_warnings))
        return "\n".join(lines)


def validate_article(article: dict) -> ValidationResult:
    """
    Validate a generated article dict.
    `article` must have at minimum: headline, body_html, meta_description, slug, category
    Returns a ValidationResult. `passed` is False if any hard failure is found.
    """
    result = ValidationResult(passed=True)

    # Concatenate all text fields for scanning
    full_text_parts = [
        article.get("headline", ""),
        article.get("meta_description", ""),
        article.get("body_html", ""),
        article.get("cta_headline", ""),
        article.get("cta_body", ""),
    ]
    for faq in article.get("faq", []):
        full_text_parts.append(faq.get("question", ""))
        full_text_parts.append(faq.get("answer", ""))
    full_text = " ".join(full_text_parts)

    # ── Hard failure: em dash ────────────────────────────────────────────────
    positions = [i for i, c in enumerate(full_text) if c == EM_DASH]
    if positions:
        result.em_dash_fail = True
        result.em_dash_positions = positions
        result.passed = False

    # ── Structural checks ────────────────────────────────────────────────────
    body = article.get("body_html", "")

    # Missing or empty headline
    if not article.get("headline", "").strip():
        result.structural_errors.append("Missing headline")
        result.passed = False

    # Missing meta description
    if not article.get("meta_description", "").strip():
        result.structural_errors.append("Missing meta description")
        result.passed = False

    # Missing slug
    if not article.get("slug", "").strip():
        result.structural_errors.append("Missing slug")
        result.passed = False

    # Missing category
    if not article.get("category", "").strip():
        result.structural_errors.append("Missing category")
        result.passed = False

    # H1 checks (body_html should NOT contain h1 — the page template handles that)
    h1_count = len(re.findall(r'<h1[\s>]', body, re.IGNORECASE))
    if h1_count > 0:
        result.structural_errors.append(f"Body HTML contains {h1_count} H1 tag(s) — H1 is rendered by the page template from the headline field")
        result.passed = False

    # At least one H2
    h2_count = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    if h2_count == 0:
        result.structural_errors.append("Body has no H2 headings")
        result.passed = False

    # Excessive headings warning (more than 12 H2/H3 combined is suspicious)
    h3_count = len(re.findall(r'<h3[\s>]', body, re.IGNORECASE))
    if h2_count + h3_count > 14:
        result.structural_warnings.append(f"High heading count: {h2_count} H2s + {h3_count} H3s — consider whether the structure matches the content depth")

    # Empty sections: <h2>...</h2> followed immediately by another heading
    if re.search(r'<h[23][^>]*>[^<]+</h[23]>\s*<h[23]', body, re.IGNORECASE):
        result.structural_warnings.append("Possible empty section: consecutive headings with no body content between them")

    # Minimum body length
    plain_text = re.sub(r'<[^>]+>', '', body)
    word_count = len(plain_text.split())
    if word_count < 600:
        result.structural_errors.append(f"Body word count too low: {word_count} words (minimum 600)")
        result.passed = False
    elif word_count < 900:
        result.structural_warnings.append(f"Body word count is {word_count} — below recommended minimum of 900")

    # ── Quality phrase scan ──────────────────────────────────────────────────
    full_lower = full_text.lower()
    found_phrases = []
    phrase_counts = {}
    for phrase in QUALITY_PHRASES:
        count = full_lower.count(phrase.lower())
        if count > 0:
            phrase_counts[phrase] = count
            found_phrases.append(f'"{phrase}" ×{count}')

    # Warn if more than 2 distinct quality phrases appear, or any phrase appears 3+ times
    if len(found_phrases) > 2 or any(v >= 3 for v in phrase_counts.values()):
        result.quality_warnings.append("Generic AI phrases detected: " + ", ".join(found_phrases))

    # ── Meta description length ──────────────────────────────────────────────
    meta = article.get("meta_description", "")
    if meta and (len(meta) < 100 or len(meta) > 165):
        result.structural_warnings.append(f"Meta description length {len(meta)} chars (ideal: 120-160)")

    return result


def strip_em_dashes(text: str) -> str:
    """Replace em dashes with a comma + space as a fallback correction."""
    return text.replace(EM_DASH, ", ")


def check_slug_collision(slug: str, article_index: list, blog_dir) -> Optional[str]:
    """Return an error string if the slug already exists, None if it is safe."""
    from pathlib import Path
    # Check article index
    existing_slugs = {a["slug"] for a in article_index}
    if slug in existing_slugs:
        return f"Slug '{slug}' already exists in article-index.json"
    # Check filesystem
    html_path = Path(blog_dir) / f"{slug}.html"
    if html_path.exists():
        return f"File already exists: blog/{slug}.html"
    return None


# ── Phase 3: per-field em dash scanning ─────────────────────────────────────

def _extract_text_fields(article: dict) -> list:
    """Return a list of (field_label, text) pairs covering all user-facing text."""
    fields = [
        ("title",            article.get("title", "")),
        ("excerpt",          article.get("excerpt", "")),
        ("meta_title",       article.get("meta_title", "")),
        ("meta_description", article.get("meta_description", "")),
        ("body_html",        article.get("body_html", "")),
    ]
    for i, faq_item in enumerate(article.get("faq", [])):
        fields.append((f"faq[{i}].question", faq_item.get("question", "")))
        fields.append((f"faq[{i}].answer",   faq_item.get("answer", "")))
    for i, src in enumerate(article.get("sources", [])):
        fields.append((f"sources[{i}].title", src.get("title", "")))
    return fields


def scan_fields_for_em_dashes(article: dict) -> list:
    """
    Scan every user-facing text field individually for em dashes.

    Returns a list of dicts:
        {field: str, position: int, context: str}

    An empty list means no em dashes were found.
    """
    findings = []
    for field_label, text in _extract_text_fields(article):
        for pos, ch in enumerate(text):
            if ch == EM_DASH:
                start   = max(0, pos - 30)
                end     = min(len(text), pos + 31)
                snippet = text[start:end].replace("\n", " ").replace("\r", "")
                findings.append({"field": field_label, "position": pos, "context": snippet})
    return findings


def scan_for_other_dashes(article: dict) -> list:
    """
    Scan for en dashes and other Unicode dash variants that editors may silently substitute.

    Returns a list of dicts:
        {field: str, position: int, char_name: str, context: str}

    These are warnings — not hard failures — because some punctuation (e.g. date ranges,
    numeric ranges) legitimately uses an en dash. Review manually.
    """
    warnings = []
    for field_label, text in _extract_text_fields(article):
        for pos, ch in enumerate(text):
            if ch in OTHER_DASH_CHARS:
                start   = max(0, pos - 25)
                end     = min(len(text), pos + 26)
                snippet = text[start:end].replace("\n", " ").replace("\r", "")
                warnings.append({
                    "field":     field_label,
                    "position":  pos,
                    "char_name": OTHER_DASH_CHARS[ch],
                    "context":   snippet,
                })
    return warnings


# ── Phase 3: source-completeness warning ────────────────────────────────────

def check_source_completeness(article: dict) -> list:
    """
    Warn when an article's content_type implies factual claims but sources is empty.

    Returns a list of warning strings. Empty list = no warnings.
    """
    warnings = []
    content_type = article.get("content_type", "")
    sources      = article.get("sources", [])
    if content_type in SOURCES_REQUIRED_TYPES and not sources:
        warnings.append(
            f"content_type='{content_type}' typically requires verifiable sources, "
            f"but the sources array is empty. Add at least one source or change "
            f"content_type to 'evergreen' / 'strategy-guide' if no primary sources apply."
        )
    return warnings


# ── Phase 3: search-intent overlap detection ────────────────────────────────

def _normalize_intent(text: str) -> set:
    """Lowercase, strip punctuation, split, remove stop words — for Jaccard comparison."""
    _STOP = {
        "a","an","the","and","or","but","in","on","at","to","for","of","with",
        "by","from","as","is","are","was","were","be","been","being","have",
        "has","had","do","does","did","will","would","could","should","may",
        "might","shall","can","need","dare","ought","used","how","what","when",
        "where","who","which","why","that","this","these","those","i","you",
        "he","she","it","we","they","me","him","her","us","them","my","your",
        "his","its","our","their","los","angeles","la","into","about","not",
    }
    words = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    return {w for w in words if w not in _STOP and len(w) > 1}


def check_search_intent_overlap(article: dict, registry: list) -> list:
    """
    Compare the article's normalized_search_intent and primary_keyword against
    all existing registry entries. Returns a list of warning strings.

    Two overlap signals are checked:
      1. Jaccard similarity on normalized_search_intent words ≥ 60 %
      2. SequenceMatcher ratio on primary_keyword strings ≥ 0.80
    """
    warnings = []
    new_intent  = article.get("normalized_search_intent", "")
    new_keyword = article.get("primary_keyword", "")
    new_words   = _normalize_intent(new_intent)

    for existing in registry:
        ex_slug    = existing.get("slug", "?")
        ex_title   = existing.get("title", "?")

        # Signal 1: normalized search intent Jaccard
        ex_intent = existing.get("normalized_search_intent") or existing.get("search_intent", "")
        ex_words  = _normalize_intent(ex_intent)
        union = new_words | ex_words
        if union:
            jaccard = len(new_words & ex_words) / len(union)
            if jaccard >= 0.60:
                warnings.append(
                    f"INTENT OVERLAP ({jaccard:.0%}) with '{ex_slug}' — "
                    f"'{ex_title}': new='{new_intent}' vs existing='{ex_intent}'. "
                    f"Confirm this is a genuinely distinct angle, not cannibalization."
                )
                continue  # One overlap warning per existing article is enough

        # Signal 2: primary keyword similarity
        ex_keyword = existing.get("primary_keyword", "")
        if new_keyword and ex_keyword:
            ratio = difflib.SequenceMatcher(None, new_keyword.lower(), ex_keyword.lower()).ratio()
            if ratio >= 0.80:
                warnings.append(
                    f"KEYWORD SIMILARITY ({ratio:.0%}) with '{ex_slug}' — "
                    f"new='{new_keyword}' vs existing='{ex_keyword}'. "
                    f"Review for search intent cannibalization."
                )

    return warnings


# ── Schema v2: social content validation ────────────────────────────────────

REQUIRED_CAROUSEL_FIELDS = {"slides", "caption", "hashtags", "cta"}
REQUIRED_REEL_FIELDS      = {"hook", "script", "cta", "caption", "hashtags"}
REQUIRED_UTM_FIELDS       = {"campaign", "carousel_url", "reel_url"}

def _social_em_dash_fields(social: dict) -> list:
    """Return (field_label, text) pairs for all social content text."""
    fields = []
    carousel = social.get("instagram_carousel", {})
    fields.append(("social_content.instagram_carousel.caption", carousel.get("caption", "")))
    fields.append(("social_content.instagram_carousel.cta",     carousel.get("cta", "")))
    for i, slide in enumerate(carousel.get("slides", [])):
        fields.append((f"social_content.instagram_carousel.slides[{i}].headline", slide.get("headline", "")))
        fields.append((f"social_content.instagram_carousel.slides[{i}].body",     slide.get("body", "")))
    reel = social.get("instagram_reel", {})
    fields.append(("social_content.instagram_reel.hook",    reel.get("hook", "")))
    fields.append(("social_content.instagram_reel.script",  reel.get("script", "")))
    fields.append(("social_content.instagram_reel.cta",     reel.get("cta", "")))
    fields.append(("social_content.instagram_reel.caption", reel.get("caption", "")))
    return fields


def validate_social_content(article: dict, schema_version: str) -> tuple:
    """
    Validate the social_content block of a schema v2 article.

    Returns (errors: list[str], warnings: list[str]).

    For schema v1 articles (no social_content): returns a single warning, no errors.
    For schema v2 articles: validates carousel + reel + utm structure and content.
    """
    errors   = []
    warnings = []
    label    = f"Article '{article.get('slug', '?')}'"

    if schema_version != "2":
        # v1 batch — social content is optional
        if "social_content" not in article:
            warnings.append(
                f"{label}: no social_content field (schema_version='{schema_version}'). "
                f"Batch v2 will require this field."
            )
        return errors, warnings

    # schema_version == "2" — social_content is required
    social = article.get("social_content")
    if not social:
        errors.append(
            f"{label}: schema_version='2' requires a 'social_content' block. "
            f"Add instagram_carousel, instagram_reel, and utm_tracking."
        )
        return errors, warnings

    # Validate carousel
    carousel = social.get("instagram_carousel")
    if not carousel:
        errors.append(
            f"{label}: social_content is missing 'instagram_carousel'. "
            f"Each v2 article requires an Instagram carousel."
        )
        carousel = {}
    else:
        for f in REQUIRED_CAROUSEL_FIELDS:
            if not carousel.get(f):
                errors.append(f"{label}: social_content.instagram_carousel missing required field '{f}'")
        slides = carousel.get("slides", [])
        if not isinstance(slides, list) or len(slides) < 4:
            errors.append(
                f"{label}: instagram_carousel.slides must have at least 4 slides "
                f"(got {len(slides) if isinstance(slides, list) else 0}); "
                f"target is 6-8 slides"
            )
        else:
            if len(slides) > 10:
                warnings.append(
                    f"{label}: instagram_carousel has {len(slides)} slides — "
                    f"recommended range is 6-8 slides (4-10 acceptable)"
                )
            # Validate slide content and sequential numbering
            expected_num = 1
            sequential_ok = True
            for i, slide in enumerate(slides):
                if not slide.get("headline"):
                    errors.append(f"{label}: instagram_carousel.slides[{i}] missing 'headline'")
                if not slide.get("body"):
                    errors.append(f"{label}: instagram_carousel.slides[{i}] missing 'body'")
                actual_num = slide.get("slide_number")
                if actual_num is not None and actual_num != expected_num:
                    sequential_ok = False
                expected_num += 1
            if not sequential_ok:
                warnings.append(
                    f"{label}: instagram_carousel slide numbers are not sequential (expected 1, 2, 3, ...). "
                    f"Renumber slides so slide_number matches position order."
                )

    hashtags = carousel.get("hashtags", []) if carousel else []
    if not isinstance(hashtags, list) or len(hashtags) < 3:
        warnings.append(f"{label}: instagram_carousel.hashtags should have at least 3 tags (got {len(hashtags) if isinstance(hashtags, list) else 0})")

    # Validate reel
    reel = social.get("instagram_reel")
    if not reel:
        errors.append(
            f"{label}: social_content is missing 'instagram_reel'. "
            f"Each v2 article requires an Instagram Reel script."
        )
        reel = {}
    else:
        for f in REQUIRED_REEL_FIELDS:
            if not reel.get(f):
                errors.append(f"{label}: social_content.instagram_reel missing required field '{f}'")

        script = reel.get("script", "")
        word_count = len(script.split()) if script else 0
        # 30-45 second reel: ~75-110 words at typical speaking pace
        if script and word_count < 75:
            warnings.append(
                f"{label}: instagram_reel.script is short ({word_count} words); "
                f"target is 75-110 words (30-45 seconds)"
            )
        if script and word_count > 110:
            warnings.append(
                f"{label}: instagram_reel.script is long ({word_count} words); "
                f"target is 75-110 words (30-45 seconds)"
            )

    # Validate UTM tracking
    utm = social.get("utm_tracking")
    if not utm:
        errors.append(
            f"{label}: social_content is missing 'utm_tracking'. "
            f"Each v2 article requires UTM tracking URLs."
        )
        utm = {}
    else:
        for f in REQUIRED_UTM_FIELDS:
            if not utm.get(f):
                errors.append(f"{label}: social_content.utm_tracking missing required field '{f}'")
        # Campaign slug must be URL-safe: lowercase letters, digits, hyphens only
        campaign = utm.get("campaign", "")
        if campaign and not re.match(r'^[a-z0-9][a-z0-9\-]*$', campaign):
            errors.append(
                f"{label}: social_content.utm_tracking.campaign '{campaign}' is not URL-safe. "
                f"Use only lowercase letters, digits, and hyphens."
            )

    # Em dash check in social content (hard failure — same rule as article body)
    for field_label, text in _social_em_dash_fields(social):
        for pos, ch in enumerate(text):
            if ch == EM_DASH:
                start   = max(0, pos - 25)
                end     = min(len(text), pos + 26)
                snippet = text[start:end].replace("\n", " ")
                errors.append(
                    f"{label}: em dash (U+2014) in '{field_label}' at position {pos}: ...{snippet}..."
                )

    return errors, warnings
