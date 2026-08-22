# Content System — Paul Sells Properties

This folder contains the editorial system for paulsellsproperties.com.

Phase 3 (current): ChatGPT acts as the editorial research and writing engine. A local Python importer validates and imports the approved batch. The existing Phase 2 publishing system (Mon/Wed/Fri at 10 AM PT) publishes approved articles automatically.

---

## How the Weekly Workflow Works

### Sunday — Research and Writing (you + ChatGPT)

**Step 1: Export editorial context**
```bash
python3 scripts/export_editorial_context.py
```
This generates `content-system/editorial-context.json` — a compact summary of everything published, scheduled, in the backlog, and on the watch list. It also includes the site page inventory for internal-link suggestions.

**Step 2: Open ChatGPT**
Open a new ChatGPT session. Paste the contents of `editorial-context.json` as your first message.

Then paste the research prompt from `content-system/CHATGPT_EDITORIAL_PROMPT.md` as your second message.

**Step 3: Research, select, approve**
ChatGPT will propose topic candidates. Review them, give feedback, and confirm the three topics for the week. ChatGPT will write each article. Review the writing, request edits, and approve each article.

**Step 4: Get the package JSON**
Once all three articles are approved, ask ChatGPT to produce the complete batch JSON package. Copy it and save it as a local file (e.g., `batch-2026-08-24.json`).

**Step 5: Import the batch**
```bash
python3 scripts/import_editorial_batch.py batch-2026-08-24.json
```
The importer will:
1. Validate all three articles (em dashes, structure, slugs, word count)
2. Show the publication schedule (Mon/Wed/Fri dates and article summaries)
3. Prompt you to confirm: type `yes` to approve or `draft` to import without scheduling

**Step 6: Commit and push**
```bash
git add blog/*.html \
    content-system/article-index.json \
    content-system/editorial-backlog.json \
    content-system/editorial-watch-list.json
git commit -m "Editorial batch: week of 2026-08-24"
git push origin main
```

### Monday / Wednesday / Friday at 10 AM PT — Automatic Publishing

A GitHub Actions workflow (`publish-scheduled.yml`) runs automatically at both 17:00 and 18:00 UTC (covering both PDT and PST year-round). It:
1. Finds articles with `status="approved"` and `scheduled_publish_at` ≤ now
2. Sets `status="published"` and records `published_at`
3. Rebuilds the homepage, blog archive, sitemap, and RSS feed
4. Commits and pushes to main
5. GitHub Pages deploys automatically after the push

**You do not need to do anything on publish days.** Articles publish themselves on schedule.

---

## Key Files

| File | Purpose |
|------|---------|
| `article-index.json` | Registry of all articles: metadata, status, lifecycle fields |
| `config.json` | System configuration (site URL, author name, model settings) |
| `editorial-backlog.json` | Topics considered but not yet selected |
| `editorial-watch-list.json` | Developing stories being monitored |
| `editorial-context.json` | Generated each Sunday; paste into ChatGPT. Not committed to git. |
| `approved-batches/` | Archive of imported batch files. Not committed to git. |
| `EDITORIAL_GUIDELINES.md` | Voice, tone, prohibitions, structural rules, audience taxonomy |
| `PACKAGE_SCHEMA.md` | Formal schema for the approved batch JSON format |
| `CHATGPT_EDITORIAL_PROMPT.md` | The master prompt to paste into ChatGPT each Sunday |

---

## Scripts

| Script | Usage |
|--------|-------|
| `export_editorial_context.py` | Generates the weekly ChatGPT context file |
| `import_editorial_batch.py` | Imports a ChatGPT-produced approved batch |
| `publish_scheduled.py` | Runs automatically via GitHub Actions on Mon/Wed/Fri |
| `site_updater.py` | Rebuilds all public surfaces from article-index.json |

---

## Article Lifecycle

```
ChatGPT writes → Paul approves → import_editorial_batch.py
                                         ↓
                              status = "approved"
                              scheduled_publish_at = Mon/Wed/Fri 10 AM PT
                                         ↓
                              publish_scheduled.py runs
                                         ↓
                              status = "published"
                              published_at = actual publish time
                                         ↓
                              site_updater rebuilds all public surfaces
                                         ↓
                              GitHub Pages deploys
```

Articles in `"draft"` status are never published automatically.
Articles in `"approved"` status publish on the next eligible Mon/Wed/Fri run.
Articles in `"published"` status are never re-processed.

---

## How to Import a Draft (No Publishing Schedule)

If you want to import articles for review without scheduling them:
```bash
python3 scripts/import_editorial_batch.py batch-2026-08-24.json --draft
```
Draft articles get HTML files and registry entries but no `scheduled_publish_at`. They will not publish until you manually set `status: "approved"` and assign a `scheduled_publish_at` in `article-index.json`.

---

## How to Trigger a Manual Publish

If you need to publish articles outside the scheduled Mon/Wed/Fri window:
1. Go to the GitHub repository
2. Click **Actions** → **Publish Scheduled Articles**
3. Click **Run workflow**
4. Leave **Dry run** unchecked
5. Click **Run workflow**

This publishes any overdue approved articles immediately.

---

## How to Check What Will Publish Next

Run the publish script in dry-run mode locally:
```bash
DRY_RUN=true python3 scripts/publish_scheduled.py
```
(Or trigger the workflow with Dry run checked on GitHub Actions.)

---

## DST and Scheduling

The publish workflow cron runs at both 17:00 UTC and 18:00 UTC on Mon/Wed/Fri.

- PDT (Mar–Nov): 10:00 AM = 17:00 UTC
- PST (Nov–Mar): 10:00 AM = 18:00 UTC

The Python script (`publish_scheduled.py`) is the authority. It reads the current time in `America/Los_Angeles` via `ZoneInfo`, so an article's `scheduled_publish_at` of `2026-12-01T10:00:00-08:00` is only satisfied when LA time reaches 10:00 AM PST — which is 18:00 UTC. The 17:00 UTC run during PST sees `now_la = 9:00 AM` and correctly skips the article.

No manual cron changes are needed when clocks change. The system handles DST automatically.

---

## Editing the Editorial Guidelines

Edit `content-system/EDITORIAL_GUIDELINES.md`. This file defines voice, prohibited phrases, the em dash prohibition, source requirements, audience taxonomy, content freshness types, and pillar/supporting article architecture.

ChatGPT should receive the relevant sections of this file as context before writing.

---

## The Em Dash Rule

**This is the most important validation rule in the system.**

The em dash character (—, Unicode U+2014) must never appear anywhere in published content: titles, headlines, body text, excerpts, metadata, FAQ answers, CTAs.

The importer scans every user-facing text field individually and reports the exact field name and character position if an em dash is found. A single em dash in any field of any article aborts the entire batch.

If ChatGPT produces an em dash, correct it in the batch file before re-running the importer.

Use a comma, semicolon, colon, or restructure the sentence instead.

---

## Autonomous Generation (Disabled)

The system includes an autonomous generation pipeline (`run_weekly_batch.py`) that would call OpenAI's API to research topics and write articles without ChatGPT involvement. This pipeline is **intentionally disabled**.

The autonomous cron trigger in `.github/workflows/generate-articles.yml` is commented out. To see whether it would run, check the workflow file.

The Phase 3 ChatGPT bridge is the active editorial path. The autonomous pipeline may be revisited in a future phase.

---

## Article Index Schema

`content-system/article-index.json` is the single source of truth for all article metadata.

Phase 3 adds these fields to new entries:
- `normalized_search_intent` — simplified search intent for deduplication
- `neighborhood` — specific LA neighborhood (or null)
- `pillar_relationship` — null | "pillar" | "supporting:slug"
- `action_type` — "new" | "supporting"
- `content_freshness_type` — freshness classification
- `sources` — structured source objects
- `audiences` — array (same values as `audience`, kept for compatibility)

Existing entries (Phase 1/2 articles) do not have these fields. They remain valid and are used in the deduplication check against whatever fields they do have.
