# Approved Editorial Batch — Package Schema

**Current version: v2** (v1 batches are still accepted but will produce a warning when `social_content` is absent)

This document defines the exact JSON structure ChatGPT must produce at the end of each weekly editorial session. The structure is validated by `scripts/import_editorial_batch.py` before any file is written.

---

## Top-Level Structure

```json
{
  "schema_version": "2",
  "batch_week": "YYYY-MM-DD",
  "generated_by": "ChatGPT",
  "approved_at": "ISO 8601 datetime with TZ offset",
  "articles": [ /* 3 article objects — each must include social_content */ ],
  "backlog_updates": [ /* 0 or more backlog entries */ ],
  "watch_list_updates": [ /* 0 or more watch-list entries */ ]
}
```

### Top-Level Fields

| Field | Required | Description |
|-------|----------|-------------|
| `schema_version` | ✓ | `"2"` for all new batches. `"1"` accepted with a warning (social_content not required). |
| `batch_week` | ✓ | ISO date of the **Monday** that begins the publication week. Example: `"2026-08-24"` schedules Mon Aug 24, Wed Aug 26, Fri Aug 28. |
| `generated_by` | | `"ChatGPT"` |
| `approved_at` | | ISO 8601 datetime when Paul approved the package |
| `articles` | ✓ | Array of 3 article objects (see below). Each must include `social_content` in v2. |
| `backlog_updates` | | Array of topic entries to merge into the backlog |
| `watch_list_updates` | | Array of story entries to merge into the watch list |

---

## Article Object

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Full article title. No em dashes. This becomes the HTML `<h1>` and `<title>` tag. |
| `slug` | string | URL-safe identifier. Lowercase, hyphens only. Example: `"condo-financing-los-angeles"` |
| `category` | string | One of the established categories (see taxonomy below) |
| `article_type` | string | `"A"` (Timely), `"B"` (Evergreen), or `"C"` (Authority/Investment) |
| `body_html` | string | Complete article body HTML. Must **not** contain `<h1>` tags. Must contain at least one `<h2>`. Must not contain em dashes. Minimum 900 words. |
| `excerpt` | string | 1–2 sentence summary for homepage/archive cards and RSS. No em dashes. |
| `meta_description` | string | 120–160 characters for search results. No em dashes. |
| `search_intent` | string | Natural language description of what the reader is trying to accomplish |
| `normalized_search_intent` | string | Simplified form of the search intent for deduplication. Lowercase, no stop words. Example: `"condo financing los angeles buyers"` |
| `audiences` | array | One or more audience identifiers from the audience taxonomy |
| `geographic_focus` | string | Geographic scope. Be specific: `"City of Los Angeles"` vs `"Los Angeles County"` vs `"West Los Angeles"` |
| `content_type` | string | Classification of the content's nature (see content types below) |
| `primary_keyword` | string | The main search phrase this article targets |
| `social_content` | object | **Required in schema v2.** See Social Content section below. |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `meta_title` | string | Override for the browser `<title>`. Defaults to `"{title} \| Paul Adams II"` if omitted. |
| `secondary_keywords` | array | Supporting keyword phrases |
| `primary_topic` | string | Broader topic description (if different from primary_keyword) |
| `neighborhood` | string or null | Specific LA neighborhood if geographically focused |
| `faq` | array | Structured FAQ items `[{"question": "...", "answer": "..."}]`. Also include FAQ inline in `body_html`. Used for em-dash scanning. |
| `sources` | array | Source objects (see Sources section below). **Required** when `content_type` is `news`, `regulatory`, or `market_data`. |
| `internal_link_suggestions` | array | `[{"anchor_text": "...", "url": "/relative/path.html"}]` |
| `related_article_suggestions` | array | Slugs of related published articles |
| `pillar_relationship` | string or null | `null`, `"pillar"`, or `"supporting:target-slug"` |
| `action_type` | string | `"new"` (default) or `"supporting"`. Note: `"update_existing"` is **not yet supported**. |
| `content_freshness_type` | string | See content freshness types below |
| `review_after` | string | ISO date when this article should next be reviewed for accuracy |
| `created_at` | string | ISO 8601 datetime when ChatGPT produced this article |
| `updated_at` | string | ISO 8601 datetime when Paul approved this article |

---

## Sources Object

```json
{
  "name":           "City of Los Angeles",
  "title":          "Rent Stabilization Ordinance — Current Eligible Units",
  "url":            "https://hcidla.lacity.org/rso",
  "published_date": "2026-01-01",
  "accessed_date":  "2026-08-24",
  "source_type":    "primary"
}
```

| Field | Description |
|-------|-------------|
| `name` | Organization or publication name |
| `title` | Title of the specific document, page, or article |
| `url` | Direct link to the source |
| `published_date` | ISO date when the source was published (approximate if needed) |
| `accessed_date` | ISO date when ChatGPT accessed the source |
| `source_type` | `"primary"` (government, official), `"secondary"` (journalism, analysis), `"data"` (statistics, databases) |

---

## Social Content Object (Required in v2)

Every v2 article must include a `social_content` block. This content is for **manual posting only** — it is never published automatically.

```json
{
  "social_content": {
    "instagram_carousel": {
      "slides": [
        {
          "slide_number": 1,
          "headline": "Cover headline (5-8 words)",
          "body": "Short subtitle that frames the topic for the reader."
        },
        {
          "slide_number": 2,
          "headline": "Key insight one",
          "body": "One to two sentences explaining this point clearly."
        },
        {
          "slide_number": 3,
          "headline": "Key insight two",
          "body": "One to two sentences. Each slide should stand alone."
        },
        {
          "slide_number": 4,
          "headline": "Key insight three",
          "body": "One to two sentences. Written the way Paul would say it."
        },
        {
          "slide_number": 5,
          "headline": "Key insight four",
          "body": "One to two sentences. No em dashes anywhere."
        },
        {
          "slide_number": 6,
          "headline": "Read the full breakdown",
          "body": "Link in bio for the complete guide."
        }
      ],
      "caption": "Carousel caption, 100-200 words. Conversational. Explains why this matters in plain language. Ends with a direct question to the reader or a clear CTA. No em dashes.",
      "hashtags": ["#LosAngeles", "#LARealEstate", "#LAHomeBuyers", "#CondoBuying", "#RealEstateTips"],
      "cta": "Link in bio"
    },
    "instagram_reel": {
      "target_duration_seconds": 40,
      "hook": "Opening line for first 3 seconds — a question or surprising fact that stops the scroll.",
      "script": "Full spoken script from hook through CTA. 75-110 words. Written as spoken word, not prose. Natural contractions are fine. Three to four key points. Ends with a single clear action.",
      "cta": "Call-to-action at end of script, e.g. Save this. Link in bio.",
      "caption": "Reel caption, 75-150 words. Can differ from the carousel caption.",
      "hashtags": ["#LosAngeles", "#LARealEstate", "#RealEstateTips", "#LAHomeBuyers"]
    },
    "utm_tracking": {
      "campaign": "article-slug",
      "carousel_url": "https://paulsellsproperties.com/blog/article-slug.html?utm_source=instagram&utm_medium=carousel&utm_campaign=article-slug",
      "reel_url": "https://paulsellsproperties.com/blog/article-slug.html?utm_source=instagram&utm_medium=reel&utm_campaign=article-slug"
    }
  }
}
```

### Social Content Validation Rules

| Rule | Result |
|------|--------|
| `social_content` missing entirely in a v2 article | **Hard failure** — batch rejected |
| `instagram_carousel` key missing | **Hard failure** |
| `instagram_reel` key missing | **Hard failure** |
| `utm_tracking` key missing | **Hard failure** |
| `instagram_carousel.caption` empty or missing | **Hard failure** |
| `instagram_carousel.cta` empty or missing | **Hard failure** |
| `instagram_carousel.hashtags` missing | **Hard failure** |
| `instagram_carousel.slides` has fewer than 4 slides | **Hard failure** (target is 6-8) |
| Each slide missing `headline` or `body` | **Hard failure** |
| `instagram_reel.hook` empty or missing | **Hard failure** |
| `instagram_reel.script` empty or missing | **Hard failure** |
| `instagram_reel.cta` empty or missing | **Hard failure** |
| `instagram_reel.caption` empty or missing | **Hard failure** |
| `instagram_reel.hashtags` missing | **Hard failure** |
| `utm_tracking.campaign` empty or missing | **Hard failure** |
| `utm_tracking.carousel_url` empty or missing | **Hard failure** |
| `utm_tracking.reel_url` empty or missing | **Hard failure** |
| Em dash (U+2014) in any social content field | **Hard failure** (same rule as article body) |
| `utm_tracking.campaign` not URL-safe (not lowercase letters/digits/hyphens) | **Hard failure** |
| Fewer than 3 hashtags on either platform | Warning only |
| Reel script under 75 words | Warning — may be too short for 30-second target |
| Reel script over 110 words | Warning — may exceed 45-second target |
| Slide numbers not sequential (1, 2, 4 instead of 1, 2, 3) | Warning — renumber slides |
| Carousel has more than 10 slides | Warning — recommended range is 6-8 |

### Social Content Voice and Format

- Write in Paul's voice: knowledgeable, direct, warm. Not corporate, not breathless.
- No em dashes anywhere in any social content field.
- No claims of legal compliance.
- Carousel headlines: 5–8 words, punchy. Body: 1–2 sentences per slide, written to stand alone.
- Reel hook: a question or surprising fact. Must stop the scroll in the first 3 seconds.
- Reel script: spoken word. Write the way you'd say it out loud. Contractions are fine. Short punchy sentences.
- UTM campaign slug: lowercase, hyphens, URL-safe. Derived from the article slug.
- Hashtags: mix broad (#LARealEstate) and specific (#LACondoBuyers, #BeverlyHillsHomes).
- Social copy must be factually consistent with the article body. No statistics in social that don't appear in the article.

---

## Backlog Entry Object

```json
{
  "id":                 "20260824-bkl-001",
  "topic":              "2028 Olympics housing demand in West LA",
  "category":           "Market Analysis",
  "audiences":          ["investors", "sellers"],
  "geography":          "West Los Angeles",
  "keyword_opportunity": "2028 Olympics los angeles real estate",
  "reason_to_consider": "Infrastructure spend and housing demand visible now; Olympic venues concentrate in West LA",
  "evergreen":          false,
  "priority":           "medium",
  "discovered_at":      "2026-08-24",
  "notes":              "",
  "source":             "LA Times, August 2026",
  "status":             "pending"
}
```

The `id` field is optional — the importer auto-generates it as `YYYYMMDD-bkl-NNN` if not provided. If an `id` matches an existing backlog entry, the importer merges the update (does not create a duplicate).

`priority`: `"low"`, `"medium"`, or `"high"`
`status`: `"pending"` (default), `"selected"`, `"expired"`, or `"dismissed"`

---

## Watch-List Entry Object

```json
{
  "id":                "20260824-wch-001",
  "story":             "California SB 1234 — Tenant Notice Period Expansion",
  "entity":            "California Legislature",
  "geography":         "Statewide / Los Angeles",
  "discovered_at":     "2026-08-24",
  "expected_milestone": "Committee vote September 2026",
  "source":            "California Legislature website",
  "relevance":         "Affects landlord notice requirements; article-worthy if enacted",
  "audiences":         ["landlords", "investors"],
  "current_status":    "In committee",
  "next_review_date":  "2026-09-15",
  "status":            "active"
}
```

The `id` field is optional — auto-generated as `YYYYMMDD-wch-NNN` if not provided. If an `id` matches an existing entry, the importer merges the update.

`status`: `"active"` (default), `"published"`, `"expired"`, or `"dismissed"`

---

## Taxonomy Reference

### Article Types
- `A` — Timely / Market Intelligence (current events, legislation, market shifts)
- `B` — Evergreen Search / Consumer Education (durable guides, financing, neighborhoods)
- `C` — Authority / Investment (analytical, investment strategy, multifamily)

### Categories
- Buyer's Guide
- Buyer Strategy
- Seller Strategy
- Market Analysis
- Investor Strategy
- Real Estate Investing
- Landlord & Rental Laws
- Condo / HOA
- Neighborhood
- Lifestyle
- Financing
- Multifamily

### Audience Taxonomy
- buyers, first-time buyers, move-up buyers, luxury buyers, lifestyle buyers
- sellers
- investors, landlords, rental property owners, duplex owners
- condo owners, homeowners

### Content Types
- `evergreen` — Durable topics, valid indefinitely with minor updates
- `news` — Breaking / time-sensitive (requires sources)
- `regulatory` — Laws, ordinances, policy changes (requires sources)
- `market_data` — Market statistics, trends, forecasts (requires sources)
- `strategy-guide` — Decision frameworks and analytical guides
- `evergreen-guide` — Extended reference guides
- `market-analysis` — In-depth market analysis
- `market-insight` — Market observations with strategic context
- `legal-regulatory` — Legal requirements and compliance
- `lifestyle` — Lifestyle, neighborhood character, quality of life
- `periodic` — Seasonal or recurring topics

### Content Freshness Types
- `evergreen` — Valid indefinitely
- `news` — Valid for days to weeks
- `periodic` — Valid for a season or year
- `regulatory` — Valid until the law/policy changes
- `market_data` — Valid until next data release

---

## Hard Validation Rules (Enforced by Importer)

The importer will **abort the entire batch** (no files written) if any article violates:

1. Em dash (—, U+2014) anywhere in: `title`, `excerpt`, `meta_title`, `meta_description`, `body_html`, any FAQ question or answer, any source title, or any `social_content` field
2. `<h1>` tag inside `body_html`
3. No `<h2>` tag inside `body_html`
4. Body word count below 600
5. Missing any required article field
6. Slug collision with an existing article (registry or filesystem)
7. `action_type: "update_existing"` (not yet implemented)
8. Invalid `article_type` (must be A, B, or C)
9. `social_content` missing in a schema v2 article
10. `instagram_carousel` missing from `social_content`
11. `instagram_reel` missing from `social_content`
12. `utm_tracking` missing from `social_content`
13. Carousel has fewer than 4 slides
14. Any carousel slide missing `headline` or `body`
15. Any required carousel or reel field empty (caption, cta, hashtags, hook, script)
16. Any required UTM field empty (campaign, carousel_url, reel_url)
17. `utm_tracking.campaign` not URL-safe (must be lowercase letters, digits, hyphens)

## Warnings (Import Proceeds)

The importer will warn but continue if:
- Body word count is 600–899 (below recommended 900)
- En dash (–) or other Unicode dash variant found (may be legitimate punctuation)
- `content_type` implies factual claims but `sources` is empty
- `normalized_search_intent` overlaps ≥ 60% with an existing published article
- `primary_keyword` is ≥ 80% similar to an existing article's keyword
- Scheduled publication date is in the past (will publish on next available run)
- Reel script is under 75 words (may be too short for 30-second target)
- Reel script is over 110 words (may exceed 45-second target)
- Carousel slide numbers are not sequential
- Carousel has more than 10 slides
- Either platform has fewer than 3 hashtags

---

## Complete Example

The following is a complete, valid schema v2 batch object. All fields shown here are either required or strongly recommended. Omit optional fields you have no data for rather than leaving them as empty strings.

```json
{
  "schema_version": "2",
  "batch_week": "2026-08-24",
  "generated_by": "ChatGPT",
  "approved_at": "2026-08-23T18:30:00-07:00",
  "articles": [
    {
      "title": "What LA Condo Buyers Need to Know About Building Warrantability in 2026",
      "slug": "la-condo-warrantability-2026",
      "category": "Condo / HOA",
      "article_type": "A",
      "body_html": "<h2>Why Your Pre-Approval Does Not Cover the Building</h2><p>Most buyers assume that a pre-approval letter is good for any property they want to purchase. That assumption is incorrect. Pre-approval addresses your personal creditworthiness. It says nothing about whether a specific building qualifies for the loan program you intend to use.</p><h2>What a Warrantability Review Actually Checks</h2><p>Fannie Mae and Freddie Mac each publish guidelines for which condo buildings they will accept as collateral for loans they purchase from lenders. Buildings with high investor ownership ratios, deferred maintenance in the reserve study, pending litigation, or inadequate HOA reserve funds can fail this review.</p>",
      "excerpt": "Most LA condo buyers do not realize that their loan approval covers their finances, not the building. Here is what to check before making an offer.",
      "meta_description": "What condo buyers in Los Angeles need to know about building warrantability in 2026, including HOA reviews, financing options, and due diligence steps.",
      "search_intent": "Buyer researching why financing fell through on a condo in Los Angeles",
      "normalized_search_intent": "condo warrantability los angeles buyers 2026",
      "audiences": ["buyers", "condo owners"],
      "geographic_focus": "City of Los Angeles",
      "content_type": "market-analysis",
      "primary_keyword": "LA condo warrantability 2026",
      "secondary_keywords": ["HOA warrantability review", "condo financing Los Angeles"],
      "sources": [
        {
          "name": "Fannie Mae",
          "title": "B4-2.1-01: General Information on Project Standards",
          "url": "https://selling-guide.fanniemae.com/",
          "published_date": "2025-11-01",
          "accessed_date": "2026-08-22",
          "source_type": "primary"
        }
      ],
      "action_type": "new",
      "social_content": {
        "instagram_carousel": {
          "slides": [
            {
              "slide_number": 1,
              "headline": "Your pre-approval does not cover the building",
              "body": "Here is what most LA condo buyers find out too late."
            },
            {
              "slide_number": 2,
              "headline": "Pre-approval covers you, not the building",
              "body": "Lenders also check whether the building itself qualifies for your loan type. If it does not, the deal can fall apart even with perfect credit."
            },
            {
              "slide_number": 3,
              "headline": "High investor ownership is a red flag",
              "body": "Buildings with more than 35-50% investor-owned units often fail conventional financing guidelines. Ask before you get attached."
            },
            {
              "slide_number": 4,
              "headline": "Deferred maintenance triggers the review",
              "body": "If the HOA has been putting off major repairs, the reserve study may show it. Lenders see this and may decline to finance in that building."
            },
            {
              "slide_number": 5,
              "headline": "Portfolio lenders are an option, but cost more",
              "body": "They can finance non-warrantable buildings, but typically require 25-30% down and charge a rate premium."
            },
            {
              "slide_number": 6,
              "headline": "Ask about warrantability before you fall in love with a unit",
              "body": "Full guide in bio. Covers the checklist, what to ask the HOA, and how to protect yourself in escrow."
            }
          ],
          "caption": "Most condo buyers in Los Angeles get a pre-approval letter and assume it covers any property they want to buy. It does not. The pre-approval covers your finances. Whether the building itself qualifies for your loan is a separate review entirely, and buildings with HOA issues, deferred maintenance, or high investor ownership can fail it. When that happens, your conventional loan does not work in that building, regardless of your credit score. I put together a full breakdown of what to check before making an offer on any LA condo. Link in bio.",
          "hashtags": ["#LosAngeles", "#LARealEstate", "#LACondoBuying", "#HOA", "#CondoBuyers", "#RealEstateTips"],
          "cta": "Link in bio"
        },
        "instagram_reel": {
          "target_duration_seconds": 38,
          "hook": "Most LA condo buyers find this out during escrow. Do not let that be you.",
          "script": "Your pre-approval letter does not mean you can buy any condo you want. It covers your finances. It says nothing about whether the building qualifies for your loan. Lenders run what is called a warrantability review on the building itself. Buildings with too many investor-owned units, deferred maintenance, or HOA reserve issues can fail it. When that happens, conventional financing does not work in that building. You are stuck either walking away or going to a portfolio lender with a higher rate and bigger down payment. Before you make an offer, ask about the building. Full checklist in bio.",
          "cta": "Save this before your next condo search. Link in bio.",
          "caption": "The pre-approval does not cover the building. Before you fall in love with a unit in Los Angeles, ask these questions about the HOA. Full breakdown at the link in bio.",
          "hashtags": ["#LosAngeles", "#LARealEstate", "#CondoBuying", "#RealEstateTips", "#LAHomeBuyers"]
        },
        "utm_tracking": {
          "campaign": "la-condo-warrantability-2026",
          "carousel_url": "https://paulsellsproperties.com/blog/la-condo-warrantability-2026.html?utm_source=instagram&utm_medium=carousel&utm_campaign=la-condo-warrantability-2026",
          "reel_url": "https://paulsellsproperties.com/blog/la-condo-warrantability-2026.html?utm_source=instagram&utm_medium=reel&utm_campaign=la-condo-warrantability-2026"
        }
      }
    }
  ],
  "backlog_updates": [
    {
      "topic": "ADU financing changes in Los Angeles 2027",
      "category": "Financing",
      "audiences": ["investors", "homeowners"],
      "geography": "City of Los Angeles",
      "keyword_opportunity": "ADU financing los angeles 2027",
      "reason_to_consider": "State law changes expanding ADU financing options take effect January 2027; article-worthy once rules are final",
      "evergreen": false,
      "priority": "medium",
      "discovered_at": "2026-08-24",
      "status": "pending"
    }
  ],
  "watch_list_updates": []
}
```

For archived batch files after import, see `content-system/approved-batches/`.
A full test fixture is available in `scripts/test_phase3.py` (the `VALID_SOCIAL` constant and `TestSchemaV2` class).
