"""Article validation: em dash prohibition, quality checks, structural checks."""
import re
from dataclasses import dataclass, field
from typing import Optional


EM_DASH = "—"

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
