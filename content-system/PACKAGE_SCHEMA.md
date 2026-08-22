# Approved Editorial Batch — Package Schema v1

This document defines the exact JSON structure ChatGPT must produce at the end of each weekly editorial session. The structure is validated by `scripts/import_editorial_batch.py` before any file is written.

---

## Top-Level Structure

```json
{
  "schema_version": "1",
  "batch_week": "YYYY-MM-DD",
  "generated_by": "ChatGPT",
  "approved_at": "ISO 8601 datetime with TZ offset",
  "articles": [ /* 3 article objects */ ],
  "backlog_updates": [ /* 0 or more backlog entries */ ],
  "watch_list_updates": [ /* 0 or more watch-list entries */ ]
}
```

### Top-Level Fields

| Field | Required | Description |
|-------|----------|-------------|
| `schema_version` | ✓ | Always `"1"` |
| `batch_week` | ✓ | ISO date of the **Monday** that begins the publication week. Example: `"2026-08-24"` schedules Mon Aug 24, Wed Aug 26, Fri Aug 28. |
| `generated_by` | | `"ChatGPT"` |
| `approved_at` | | ISO 8601 datetime when Paul approved the package |
| `articles` | ✓ | Array of 3 article objects (see below) |
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
| `action_type` | string | `"new"` (default) or `"supporting"`. Note: `"update_existing"` is **not yet supported** in Phase 3. |
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

1. Em dash (—, U+2014) anywhere in: `title`, `excerpt`, `meta_title`, `meta_description`, `body_html`, any FAQ question or answer, any source title
2. `<h1>` tag inside `body_html`
3. No `<h2>` tag inside `body_html`
4. Body word count below 600
5. Missing any required field
6. Slug collision with an existing article (registry or filesystem)
7. `action_type: "update_existing"` (not yet implemented)
8. Invalid `article_type` (must be A, B, or C)

## Warnings (Import Proceeds)

The importer will warn but continue if:
- Body word count is 600–899 (below recommended 900)
- En dash (–) or other Unicode dash variant found (may be legitimate punctuation)
- `content_type` implies factual claims but `sources` is empty
- `normalized_search_intent` overlaps ≥ 60% with an existing published article
- `primary_keyword` is ≥ 80% similar to an existing article's keyword
- Scheduled publication date is in the past (will publish on next available run)

---

## Complete Example

See `content-system/approved-batches/` for archived batch files after import.
A test fixture is available at `scripts/test_phase3.py`.
