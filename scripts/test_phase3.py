#!/usr/bin/env python3
"""
Phase 3 test suite — 21 test cases covering the editorial import pipeline.

Run:
    python3 scripts/test_phase3.py

Tests:
    1.  Valid three-article batch
    2.  Invalid JSON
    3.  Missing required field
    4.  Em dash in title
    5.  Em dash buried inside body_html
    6.  Em dash in FAQ answer
    7.  Duplicate slug (in registry)
    8.  Search intent overlap warning
    9.  Empty sources for news article
    10. update_existing action_type
    11. Draft import
    12. Approval cancellation (non-interactive mode)
    13. Mon/Wed/Fri date calculation — nominal week (2026-08-24)
    14. Month boundary (2026-08-31)
    15. Year boundary (2026-12-28)
    16. Leap year (2028-02-28)
    17. Existing backlog item update (same id)
    18. New backlog item
    19. Existing watch-list item update (same id)
    20. New watch-list item
    21. Failure of article #3 causes zero writes for articles #1 and #2
"""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Ensure scripts/ is on the path
sys.path.insert(0, str(Path(__file__).parent))

from import_editorial_batch import (
    _merge_entries,
    _next_pub_slots,
    _validate_batch_schema,
    _validate_single_article,
    run_import,
)
from validator import (
    check_search_intent_overlap,
    check_source_completeness,
    scan_fields_for_em_dashes,
    scan_for_other_dashes,
    validate_social_content,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

VALID_BODY = """<h2>What Changed in the Los Angeles Condo Market</h2>
<p>Los Angeles condo buyers in 2026 are encountering a market that looks different from
even two years ago. Lender scrutiny of homeowner associations has intensified, interest
rate pressure has altered affordability calculations for a significant portion of the
buyer pool, and the inventory picture varies sharply depending on the neighborhood and
price point. Understanding each of these forces separately is less useful than
understanding how they interact, because the interaction is what determines whether a
specific condo in a specific building at a specific price represents a sound purchase.</p>

<p>The most significant change is the tightening of warrantability requirements. Fannie
Mae and Freddie Mac both updated their condo project approval guidelines in the past
eighteen months, placing new scrutiny on buildings with deferred maintenance, high
commercial space ratios, high investor ownership percentages, and HOAs that have
inadequate reserve funds. A building that was easily financeable in 2023 may now
require additional documentation, a portfolio lender, or a substantially larger down
payment to close.</p>

<h2>How Lender Requirements Affect Your Options</h2>
<p>Buyers who receive pre-approval letters often assume those letters are valid for any
condo they want to purchase. That assumption is incorrect. Pre-approval addresses your
personal creditworthiness and income; it says nothing about whether a specific building
qualifies for the loan program you intend to use. A building that fails the
warrantability review cannot be financed with a conventional Fannie Mae or Freddie Mac
loan, regardless of how strong your personal financial profile is.</p>

<p>The practical effect is that your effective buying pool is smaller than your pre-approval
suggests. A building in Koreatown with $800,000 units may be effectively unavailable
to you if it has a high percentage of investor-owned units, a deferred elevator
replacement in the reserve study, or pending special assessments the HOA has not yet
formalized. Before getting emotionally attached to any condo listing, ask your agent
to request the HOA documents and run a basic warrantability check with your lender.</p>

<p>Portfolio lenders, which hold loans on their own books rather than selling them to
the secondary market, operate under different guidelines. They can finance buildings
that Fannie Mae and Freddie Mac will not, but they typically charge higher interest
rates, require larger down payments (often 25 to 30 percent), and may impose
prepayment penalties. For buyers in buildings with known warrantability issues, this
is sometimes the only viable financing path.</p>

<h2>What the Inventory Picture Looks Like</h2>
<p>Condo inventory in Los Angeles has been gradually increasing since mid-2025, but the
increase is not uniform. The bulk of the new supply is concentrated in the mid-market
range, roughly $600,000 to $1.2 million, where affordability constraints have been
sharpest and where seller motivation to transact has increased as the carrying cost of
waiting has risen with higher rates. The luxury condo segment, particularly in
buildings with full-service amenities on the Westside and in downtown Los Angeles,
has held inventory tighter and prices firmer.</p>

<p>For buyers, the implication is that patient, well-prepared purchasers in the
mid-market range have more negotiating leverage today than at any point in the past
three years. That leverage is conditional on financing certainty: a buyer who needs
to close with a conventional loan in a building whose warrantability status is unknown
has less leverage, not more, because the deal can fall apart at the financing
contingency stage after both parties have invested time and resources.</p>

<h2>Pricing and Negotiation Strategy</h2>
<p>Condominium pricing in Los Angeles has diverged from single-family pricing in ways
that matter to buyers. While well-located single-family homes in the sub-$2 million
range continue to attract multiple offers and trade at or above asking price, condos
in many neighborhoods are trading at discounts to list price for the first time since
2019. Days on market have extended. Price reductions are more common.</p>

<p>This does not mean condos are poor investments. It means the market is correcting to
reflect the genuine carrying costs and financing friction that buyers now face. Buyers
who do their due diligence on a building's financial health, who secure financing
appropriate for that specific building, and who negotiate from a position of certainty
are well-positioned. Buyers who skip the due diligence and assume they can finance
any building with their pre-approval are setting themselves up for a failed escrow.</p>

<h2>Frequently Asked Questions</h2>

<p><strong>What is a warrantability review and why does it matter?</strong>
A warrantability review is the process lenders use to determine whether a condo
building meets the guidelines required to sell the resulting loan to Fannie Mae or
Freddie Mac. Buildings with high investor ownership ratios, inadequate HOA reserves,
pending litigation, or significant deferred maintenance often fail this review.
If a building is non-warrantable, buyers cannot use standard conventional financing
to purchase in it, which substantially limits the buyer pool and can affect resale
value. Ask about warrantability before making an offer, not during escrow.</p>

<p><strong>Can I still buy a non-warrantable condo?</strong>
Yes, but your financing options are limited. Portfolio lenders can finance
non-warrantable buildings, but they typically require 25 to 30 percent down and
charge a rate premium of 0.5 to 1.5 percentage points above conventional rates.
Cash buyers face no warrantability constraints. If you are considering a specific
building with known issues, discuss the financing path with your lender before you
make an offer, and factor the higher financing cost into your price analysis.</p>

<div class="post-cta-box">
<h3>Work with Paul Adams II</h3>
<p>Condo purchases in Los Angeles require careful due diligence on the building as
well as the unit. If you are evaluating specific buildings or want to understand
your financing options before you start searching, a conversation with an experienced
advisor is the most efficient first step.</p>
<a href="https://calendly.com/pauladamsii" target="_blank" rel="noopener" class="btn btn-primary">Schedule a Conversation</a>
</div>"""


def _make_article(overrides: dict = None) -> dict:
    """Return a minimal valid article dict."""
    art = {
        "title":                    "Understanding the Los Angeles Condo Market in 2026",
        "slug":                     "test-condo-market-2026",
        "category":                 "Market Analysis",
        "article_type":             "A",
        "body_html":                VALID_BODY,
        "excerpt":                  "An honest look at condo market dynamics and what buyers need to know right now.",
        "meta_description":         "A clear-eyed analysis of Los Angeles condo market conditions in 2026, including financing challenges and what buyers should know before making an offer.",
        "search_intent":            "Informational — buyer researching current condo market conditions",
        "normalized_search_intent": "los angeles condo market conditions 2026 buyers",
        "audiences":                ["buyers", "condo owners"],
        "geographic_focus":         "Los Angeles",
        "content_type":             "market-analysis",
        "primary_keyword":          "Los Angeles condo market 2026",
        "secondary_keywords":       ["condo financing", "HOA warrantability"],
        "sources":                  [
            {
                "name":           "CoreLogic",
                "title":          "Los Angeles Condo Market Report Q2 2026",
                "url":            "https://www.corelogic.com/reports/",
                "published_date": "2026-07-01",
                "accessed_date":  "2026-08-20",
                "source_type":    "data",
            }
        ],
        "action_type": "new",
    }
    if overrides:
        art.update(overrides)
    return art


def _make_batch(article_overrides_list=None, batch_overrides=None) -> dict:
    """Return a valid three-article batch, applying per-article or top-level overrides."""
    articles = []
    for i in range(3):
        overrides = (article_overrides_list or [None, None, None])[i]
        art = _make_article(overrides or {})
        # Unique slug per article in the default batch
        if "slug" not in (overrides or {}):
            art["slug"] = f"test-article-{i+1}"
        articles.append(art)

    batch = {
        "schema_version": "1",
        "batch_week":     "2026-08-24",
        "generated_by":   "ChatGPT",
        "articles":       articles,
        "backlog_updates":    [],
        "watch_list_updates": [],
    }
    if batch_overrides:
        batch.update(batch_overrides)
    return batch


class TestPhase3(unittest.TestCase):

    # ── Scheduling: the most foundational logic ───────────────────────────────

    def test_13_nominal_week_dates(self):
        """Mon/Wed/Fri slots for batch_week 2026-08-24 are Aug 24, Aug 26, Aug 28."""
        slots = _next_pub_slots(date(2026, 8, 24))
        self.assertEqual(len(slots), 3)
        self.assertEqual((slots[0].year, slots[0].month, slots[0].day), (2026, 8, 24))
        self.assertEqual((slots[1].year, slots[1].month, slots[1].day), (2026, 8, 26))
        self.assertEqual((slots[2].year, slots[2].month, slots[2].day), (2026, 8, 28))
        # Verify weekdays
        self.assertEqual(slots[0].weekday(), 0, "first slot must be Monday")
        self.assertEqual(slots[1].weekday(), 2, "second slot must be Wednesday")
        self.assertEqual(slots[2].weekday(), 4, "third slot must be Friday")
        # Verify time
        for slot in slots:
            self.assertEqual(slot.hour, 10)
            self.assertEqual(slot.minute, 0)

    def test_14_month_boundary(self):
        """batch_week 2026-08-31 → Aug 31, Sep 2, Sep 4."""
        slots = _next_pub_slots(date(2026, 8, 31))
        self.assertEqual((slots[0].year, slots[0].month, slots[0].day), (2026, 8, 31))
        self.assertEqual((slots[1].year, slots[1].month, slots[1].day), (2026, 9,  2))
        self.assertEqual((slots[2].year, slots[2].month, slots[2].day), (2026, 9,  4))

    def test_15_year_boundary(self):
        """batch_week 2026-12-28 → Dec 28, Dec 30, Jan 1 (2027)."""
        slots = _next_pub_slots(date(2026, 12, 28))
        self.assertEqual((slots[0].year, slots[0].month, slots[0].day), (2026, 12, 28))
        self.assertEqual((slots[1].year, slots[1].month, slots[1].day), (2026, 12, 30))
        self.assertEqual((slots[2].year, slots[2].month, slots[2].day), (2027,  1,  1))

    def test_16_leap_year(self):
        """batch_week 2028-02-28 → Feb 28, Mar 1, Mar 3 (2028 is a leap year)."""
        # Verify 2028 is a leap year
        import calendar
        self.assertTrue(calendar.isleap(2028))
        slots = _next_pub_slots(date(2028, 2, 28))
        self.assertEqual((slots[0].year, slots[0].month, slots[0].day), (2028,  2, 28))
        self.assertEqual((slots[1].year, slots[1].month, slots[1].day), (2028,  3,  1))
        self.assertEqual((slots[2].year, slots[2].month, slots[2].day), (2028,  3,  3))

    # ── Schema validation ─────────────────────────────────────────────────────

    def test_02_invalid_json(self):
        """Invalid JSON produces a parse error, not a crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "bad.json"
            batch_file.write_text("{not valid json", encoding="utf-8")
            result = run_import(batch_file, mode="approve")
        self.assertFalse(result)

    def test_03_missing_required_field(self):
        """An article missing a required field fails validation."""
        art = _make_article({"slug": ""})  # slug is empty
        errors, _ = _validate_single_article(art, [], Path("/dev/null"), 1)
        self.assertTrue(
            any("slug" in e for e in errors),
            f"Expected slug error; got: {errors}",
        )

    # ── Em dash validation ────────────────────────────────────────────────────

    def test_04_em_dash_in_title(self):
        """Em dash in title field is detected and reported."""
        art = _make_article({"title": "Buying in LA — What You Need to Know"})
        findings = scan_fields_for_em_dashes(art)
        self.assertTrue(
            any(f["field"] == "title" for f in findings),
            f"Expected em dash in title; findings: {findings}",
        )

    def test_05_em_dash_in_body(self):
        """Em dash buried in body_html is detected with position and context."""
        # Append a sentence containing an em dash after the last paragraph in the body.
        # We use string concatenation rather than .replace() so the test is independent
        # of the exact prose in VALID_BODY.
        body_with_dash = VALID_BODY + "\n<!-- em dash test — inserted here -->"
        art = _make_article({"body_html": body_with_dash})
        findings = scan_fields_for_em_dashes(art)
        body_findings = [f for f in findings if f["field"] == "body_html"]
        self.assertTrue(len(body_findings) > 0, "Expected em dash finding in body_html")
        self.assertIn("position", body_findings[0])
        self.assertIn("context", body_findings[0])
        # Context snippet should contain text on both sides of the em dash
        self.assertIn("—", body_findings[0]["context"])
        self.assertIn("position", body_findings[0])
        self.assertIn("context", body_findings[0])

    def test_06_em_dash_in_faq(self):
        """Em dash in FAQ answer is detected."""
        art = _make_article({
            "faq": [{"question": "What is this?", "answer": "This is the answer — clearly."}]
        })
        findings = scan_fields_for_em_dashes(art)
        faq_findings = [f for f in findings if "faq" in f["field"]]
        self.assertTrue(len(faq_findings) > 0, "Expected em dash finding in FAQ")

    # ── Slug collision ────────────────────────────────────────────────────────

    def test_07_duplicate_slug(self):
        """Slug collision with existing registry entry is a hard failure."""
        existing_registry = [{"slug": "test-article-1", "title": "Existing"}]
        art = _make_article({"slug": "test-article-1"})
        errors, _ = _validate_single_article(art, existing_registry, Path("/dev/null"), 1)
        self.assertTrue(
            any("test-article-1" in e and "already exists" in e for e in errors),
            f"Expected collision error; got: {errors}",
        )

    # ── Warnings (non-blocking) ───────────────────────────────────────────────

    def test_08_search_intent_overlap_warning(self):
        """Search intent overlap with existing article produces a warning."""
        existing = [{
            "slug": "condo-financing",
            "title": "Condo Financing Is Tightening",
            "primary_keyword": "condo financing Los Angeles",
            "normalized_search_intent": "condo financing los angeles buyers market 2026",
            "search_intent": "informational",
        }]
        art = _make_article({
            "primary_keyword":          "condo financing los angeles buyers",
            "normalized_search_intent": "condo financing los angeles buyers",
        })
        warnings = check_search_intent_overlap(art, existing)
        self.assertTrue(len(warnings) > 0, "Expected overlap warning")

    def test_09_empty_sources_for_news(self):
        """news content_type with empty sources produces a warning."""
        art = _make_article({"content_type": "news", "sources": []})
        warnings = check_source_completeness(art)
        self.assertEqual(len(warnings), 1)
        self.assertIn("sources", warnings[0].lower())

    # ── Action types ──────────────────────────────────────────────────────────

    def test_10_update_existing_hard_failure(self):
        """action_type='update_existing' is a hard validation failure."""
        art = _make_article({"action_type": "update_existing"})
        errors, _ = _validate_single_article(art, [], Path("/dev/null"), 1)
        self.assertTrue(
            any("update_existing" in e for e in errors),
            f"Expected update_existing error; got: {errors}",
        )

    # ── Import modes ──────────────────────────────────────────────────────────

    def test_11_draft_import(self):
        """Draft mode imports articles with status='draft' and no scheduled_publish_at."""
        batch = _make_batch()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            batch_file = tmppath / "batch.json"
            batch_file.write_text(json.dumps(batch), encoding="utf-8")

            result = self._run_import_isolated(batch_file, tmppath, mode="draft")

        self.assertTrue(result["success"])
        for entry in result["registry"]:
            self.assertEqual(entry["status"], "draft", f"Expected draft, got {entry['status']}")
            self.assertIsNone(entry["scheduled_publish_at"], "Draft should have no scheduled_publish_at")

    def test_12_cancellation_writes_nothing(self):
        """Cancellation (non-yes answer in interactive mode) writes zero files."""
        batch = _make_batch()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            batch_file = tmppath / "batch.json"
            batch_file.write_text(json.dumps(batch), encoding="utf-8")

            # Simulate user typing "no" at the prompt
            with patch("builtins.input", return_value="no"):
                result = self._run_import_isolated(batch_file, tmppath, mode="interactive")

        # No files should have been written
        self.assertFalse(result["success"])
        self.assertEqual(len(result["html_files"]), 0, "No HTML files should be written on cancel")

    # ── Test 1: full valid batch ──────────────────────────────────────────────

    def test_01_valid_batch_full_import(self):
        """A valid three-article batch imports successfully in approve mode."""
        batch = _make_batch()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            batch_file = tmppath / "batch.json"
            batch_file.write_text(json.dumps(batch), encoding="utf-8")

            result = self._run_import_isolated(batch_file, tmppath, mode="approve")

        self.assertTrue(result["success"], f"Import should succeed; result: {result}")
        self.assertEqual(len(result["html_files"]), 3, "Should create 3 HTML files")
        self.assertEqual(len(result["registry"]), 3, "Registry should have 3 entries")
        for entry in result["registry"]:
            self.assertEqual(entry["status"], "approved")
            self.assertIsNotNone(entry["scheduled_publish_at"])
        # Verify Mon/Wed/Fri dates
        dates = [e["date_iso"] for e in result["registry"]]
        self.assertIn("2026-08-24", dates)
        self.assertIn("2026-08-26", dates)
        self.assertIn("2026-08-28", dates)

    # ── Test 21: article 3 failure → zero writes ─────────────────────────────

    def test_21_article3_failure_zero_writes(self):
        """If article #3 has an em dash, ZERO articles are imported (all or nothing)."""
        overrides = [
            None,
            None,
            {"title": "Article Three — With Em Dash"},   # em dash in title
        ]
        batch = _make_batch(article_overrides_list=overrides)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            batch_file = tmppath / "batch.json"
            batch_file.write_text(json.dumps(batch), encoding="utf-8")

            result = self._run_import_isolated(batch_file, tmppath, mode="approve")

        self.assertFalse(result["success"], "Import should fail due to article 3 em dash")
        self.assertEqual(len(result["html_files"]), 0, "Zero HTML files should be written")
        self.assertEqual(len(result["registry"]), 0, "Zero registry entries should be written")

    # ── Backlog and watch-list merge ──────────────────────────────────────────

    def test_17_backlog_existing_item_update(self):
        """Existing backlog entry is updated in place when id matches."""
        current = [{"id": "20260817-bkl-001", "topic": "Olympics housing", "status": "pending"}]
        updates = [{"id": "20260817-bkl-001", "status": "selected", "notes": "Now timely"}]
        merged, stats = _merge_entries(current, updates, "2026-08-24", "bkl")
        # Should still be one entry (updated, not duplicated)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["status"], "selected")
        self.assertEqual(merged[0]["notes"], "Now timely")
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["new"], 0)

    def test_18_backlog_new_item(self):
        """New backlog entry without matching id is appended."""
        current = [{"id": "20260817-bkl-001", "topic": "Olympics housing", "status": "pending"}]
        updates = [{"topic": "ADU financing changes 2027", "status": "pending"}]
        merged, stats = _merge_entries(current, updates, "2026-08-24", "bkl")
        self.assertEqual(len(merged), 2)
        self.assertEqual(stats["new"], 1)
        self.assertEqual(stats["updated"], 0)
        # Auto-generated id should be present
        new_entry = merged[1]
        self.assertIn("id", new_entry)

    def test_19_watch_list_existing_item_update(self):
        """Existing watch-list entry is updated in place when id matches."""
        current = [{"id": "20260817-wch-001", "story": "SB 1234", "current_status": "In committee"}]
        updates = [{"id": "20260817-wch-001", "current_status": "Signed into law", "status": "published"}]
        merged, stats = _merge_entries(current, updates, "2026-08-24", "wch")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["current_status"], "Signed into law")
        self.assertEqual(stats["updated"], 1)

    def test_20_watch_list_new_item(self):
        """New watch-list entry is appended."""
        current = []
        updates = [{"story": "New LA Zoning Reform", "current_status": "Proposed"}]
        merged, stats = _merge_entries(current, updates, "2026-08-24", "wch")
        self.assertEqual(len(merged), 1)
        self.assertEqual(stats["new"], 1)
        self.assertIn("id", merged[0])

    # ── Helper: isolated import in a temp environment ─────────────────────────

    def _run_import_isolated(self, batch_file: Path, tmpdir: Path, mode: str) -> dict:
        """
        Run import_editorial_batch.run_import() with all file paths redirected to tmpdir.
        Patches cfg_module path constants to point to the temp directory.
        Returns a dict with success bool, html_files written, and registry entries.
        """
        import config as cfg_module
        import import_editorial_batch

        blog_dir   = tmpdir / "blog"
        blog_dir.mkdir(exist_ok=True)
        index_path = tmpdir / "article-index.json"
        index_path.write_text("[]", encoding="utf-8")
        backlog_path  = tmpdir / "editorial-backlog.json"
        backlog_path.write_text(json.dumps({"_schema": "1", "entries": []}), encoding="utf-8")
        watch_path    = tmpdir / "editorial-watch-list.json"
        watch_path.write_text(json.dumps({"_schema": "1", "entries": []}), encoding="utf-8")
        batches_dir   = tmpdir / "approved-batches"
        batches_dir.mkdir(exist_ok=True)

        patches = {
            "cfg_module.BLOG_DIR":           blog_dir,
            "cfg_module.ARTICLE_INDEX_PATH": index_path,
            "cfg_module.BACKLOG_PATH":       backlog_path,
            "cfg_module.WATCH_LIST_PATH":    watch_path,
            "cfg_module.APPROVED_BATCHES_DIR": batches_dir,
        }

        with patch.multiple(
            "import_editorial_batch.cfg_module",
            BLOG_DIR=blog_dir,
            ARTICLE_INDEX_PATH=index_path,
            BACKLOG_PATH=backlog_path,
            WATCH_LIST_PATH=watch_path,
            APPROVED_BATCHES_DIR=batches_dir,
        ):
            # Also patch load_article_index to read from temp dir
            orig_load = cfg_module.load_article_index
            cfg_module.load_article_index = lambda: json.loads(index_path.read_text())

            try:
                # Suppress stdout during import
                with patch("sys.stdout", new_callable=StringIO):
                    success = import_editorial_batch.run_import(batch_file, mode=mode)
            finally:
                cfg_module.load_article_index = orig_load

        html_files = list(blog_dir.glob("*.html"))
        registry   = json.loads(index_path.read_text()) if index_path.exists() else []

        return {"success": success, "html_files": html_files, "registry": registry}


# ── Schema v2 social content tests ───────────────────────────────────────────

VALID_SOCIAL = {
    "instagram_carousel": {
        "slides": [
            {"slide_number": 1, "headline": "Cover headline here", "body": "Subtitle text"},
            {"slide_number": 2, "headline": "Key point one", "body": "Explanation sentence."},
            {"slide_number": 3, "headline": "Key point two", "body": "Explanation sentence."},
            {"slide_number": 4, "headline": "Key point three", "body": "Explanation sentence."},
            {"slide_number": 5, "headline": "Read the full guide", "body": "Link in bio."},
        ],
        "caption": "Full carousel caption text here. It should be 100-200 words and conversational.",
        "hashtags": ["#LosAngeles", "#LARealEstate", "#HomeBuying"],
        "cta": "Link in bio",
    },
    "instagram_reel": {
        "target_duration_seconds": 45,
        "hook": "Did you know most LA buyers skip this critical step?",
        "script": "Here is the full spoken script for the reel. It covers three key points about buying in Los Angeles. It is written conversationally so Paul can read it naturally on camera without sounding stiff.",
        "cta": "Save this for your home search. Link in bio.",
        "caption": "Reel caption text here covering the main topic.",
        "hashtags": ["#LosAngeles", "#RealEstateTips", "#LAHomeBuyers"],
    },
    "utm_tracking": {
        "campaign": "test-article-slug",
        "carousel_url": "https://paulsellsproperties.com/blog/test-article.html?utm_source=instagram&utm_medium=carousel&utm_campaign=test-article-slug",
        "reel_url": "https://paulsellsproperties.com/blog/test-article.html?utm_source=instagram&utm_medium=reel&utm_campaign=test-article-slug",
    },
}


class TestSchemaV2(unittest.TestCase):
    """Tests for schema v2 social content validation."""

    def test_22_v1_batch_no_social_content_produces_warning(self):
        """Schema v1 batch without social_content produces a warning but not an error."""
        article = {"slug": "test-slug"}
        errors, warnings = validate_social_content(article, "1")
        self.assertEqual(errors, [], "v1 batch without social_content should not error")
        self.assertTrue(
            any("social_content" in w for w in warnings),
            "Expected a warning about missing social_content for v1 batch",
        )

    def test_23_v2_batch_missing_social_content_is_hard_failure(self):
        """Schema v2 article missing social_content entirely is a hard failure."""
        article = {"slug": "test-slug"}
        errors, warnings = validate_social_content(article, "2")
        self.assertTrue(len(errors) > 0, "Expected errors for missing social_content in v2 batch")

    def test_24_v2_valid_social_content_passes(self):
        """Schema v2 article with complete, valid social_content passes."""
        article = {"slug": "test-slug", "social_content": VALID_SOCIAL}
        errors, warnings = validate_social_content(article, "2")
        self.assertEqual(errors, [], f"Expected no errors for valid social_content, got: {errors}")

    def test_25_social_em_dash_is_hard_failure(self):
        """Em dash in carousel caption is a hard failure."""
        import copy
        bad = copy.deepcopy(VALID_SOCIAL)
        bad["instagram_carousel"]["caption"] = "Great insight — must read this"
        article = {"slug": "test-slug", "social_content": bad}
        errors, _ = validate_social_content(article, "2")
        self.assertTrue(
            any("em dash" in e for e in errors),
            "Expected em dash error in carousel caption",
        )

    def test_26_social_em_dash_in_reel_script_is_hard_failure(self):
        """Em dash in reel script is a hard failure."""
        import copy
        bad = copy.deepcopy(VALID_SOCIAL)
        bad["instagram_reel"]["script"] = "This is great — watch this reel now please."
        article = {"slug": "test-slug", "social_content": bad}
        errors, _ = validate_social_content(article, "2")
        self.assertTrue(
            any("em dash" in e for e in errors),
            "Expected em dash error in reel script",
        )

    def test_27_carousel_too_few_slides_is_error(self):
        """Carousel with fewer than 3 slides is a hard failure."""
        import copy
        bad = copy.deepcopy(VALID_SOCIAL)
        bad["instagram_carousel"]["slides"] = [
            {"slide_number": 1, "headline": "Cover", "body": "Subtitle"},
            {"slide_number": 2, "headline": "Point", "body": "Body"},
        ]
        article = {"slug": "test-slug", "social_content": bad}
        errors, _ = validate_social_content(article, "2")
        self.assertTrue(
            any("slides" in e for e in errors),
            "Expected error for too few carousel slides",
        )

    def test_28_missing_utm_tracking_is_error(self):
        """Missing utm_tracking block in v2 social_content is a hard failure."""
        import copy
        bad = copy.deepcopy(VALID_SOCIAL)
        bad.pop("utm_tracking")
        article = {"slug": "test-slug", "social_content": bad}
        errors, _ = validate_social_content(article, "2")
        self.assertTrue(
            any("utm_tracking" in e for e in errors),
            "Expected error for missing utm_tracking",
        )


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run with verbose output and a clean summary
    loader = unittest.TestLoader()
    suite_phase3 = loader.loadTestsFromTestCase(TestPhase3)
    suite_v2     = loader.loadTestsFromTestCase(TestSchemaV2)

    # Sort individual test cases by test number for readable output
    def _test_num(test):
        import re
        name = getattr(test, '_testMethodName', '')
        m = re.match(r"test_(\d+)", name)
        return int(m.group(1)) if m else 999

    suite_phase3._tests.sort(key=_test_num)
    suite_v2._tests.sort(key=_test_num)
    suite = unittest.TestSuite([suite_phase3, suite_v2])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
