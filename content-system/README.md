# Content System — Paul Sells Properties

This folder contains the editorial automation system that researches, writes, validates, and prepares weekly blog articles for paulsellsproperties.com.

## How the system works

Once per week (Sunday morning), a GitHub Actions workflow runs automatically. It:

1. Reads the existing article inventory to understand what has already been covered
2. Uses OpenAI with web search to research current Los Angeles real estate conditions
3. Generates a pool of candidate article topics and scores them
4. Selects three topics — one timely/market article, one evergreen educational article, one investment/authority article
5. Writes each article using OpenAI, following strict editorial guidelines
6. Validates every article: checks for prohibited characters, quality issues, structural problems, and metadata completeness
7. If an article fails validation, it requests a correction and tries again (up to 2 attempts)
8. Builds complete HTML pages that match the site's existing design
9. Updates the blog index, sitemap, RSS feed, and article inventory
10. Creates one pull request containing all three articles for your review

**You review the pull request. You merge it. Only your merge causes anything to go live.**

---

## How topic selection works

The system uses OpenAI with web search to research:
- Current Los Angeles real estate market conditions
- Recent legislation and policy changes
- Mortgage and financing environment
- Common buyer, seller, and investor questions
- Content gaps on the site

It generates 12+ candidate topics, scores each one across 11 dimensions (relevance, LA-specificity, client usefulness, search intent, duplication risk, etc.), and selects the three strongest topics.

Topics that substantially duplicate existing articles are rejected.

---

## How to manually suggest a topic

Edit `content-system/manual-topics.json`. Add an entry to the `topics` array:

```json
{
  "topics": [
    {
      "topic": "How rent control affects property values in Los Angeles",
      "suggested_headline": "What Rent Control Actually Does to Property Values in Los Angeles",
      "article_type": "C",
      "category": "Real Estate Investing",
      "primary_keyword": "rent control Los Angeles property value"
    }
  ]
}
```

On the next run, the system will prioritize this topic. After it is used, it is removed from the file automatically.

Leave `topics` as an empty array `[]` for fully automated topic selection.

---

## How to trigger a manual run

Go to the GitHub repository, click **Actions**, select **Weekly Article Generation**, then click **Run workflow**.

You can choose:
- **Dry run**: generates and validates articles but does not create a PR or modify any files — useful for testing
- **OpenAI model override**: use a specific model name for one run (leave blank to use the default)

---

## How to change the OpenAI model

Edit `content-system/config.json`:

```json
{
  "writing_model": "gpt-4o",
  "research_model": "gpt-4o"
}
```

Change the model name and save. The next run will use the new model.

You can also override for a single run using the model field in the manual workflow trigger.

---

## How to change the schedule

Edit `.github/workflows/generate-articles.yml`. Find the `cron:` line and change the time.

The format is UTC: `'0 15 * * 0'` means Sunday at 15:00 UTC (8:00 AM Pacific Daylight Time).

For Pacific Standard Time (winter), change to `'0 16 * * 0'`.

---

## How to review a weekly pull request

When the automation runs successfully, a pull request appears in the GitHub repository.

For each article, the PR description shows:
- Title, slug, category, and article type
- The primary search keyword
- Estimated word count
- Why the topic was selected
- Sources the article drew on
- Internal links added
- Validation status for each check

Read each article in the PR files tab before merging. You can edit article HTML directly in the PR branch if you want to make changes before publishing.

When you are satisfied, click **Merge pull request**. GitHub Pages publishes the articles immediately.

---

## How to disable the automation

Go to the GitHub repository, click **Actions**, select **Weekly Article Generation**, and click **Disable workflow**.

This stops the scheduled Sunday run. You can re-enable it at any time. Manual triggers still work.

---

## Where editorial rules live

`content-system/EDITORIAL_GUIDELINES.md`

This file defines Paul's voice, prohibited phrases, the em dash prohibition, rules on fabrication, and how to approach different article types. The automation reads this file on every run and passes it to the writing model.

---

## Where the article inventory lives

`content-system/article-index.json`

This file records every published article: title, slug, URL, date, category, keywords, audience, tags, and internal links. The automation reads it to avoid topic duplication and uses it to identify related article opportunities. It is updated automatically when new articles are approved and merged.

---

## What happens if generation fails

If an article fails validation (most commonly because it contains a prohibited em dash that could not be corrected), the workflow:
- Does not include that article in the PR
- Reports the failure in the PR description
- Continues with any articles that did pass

If all three articles fail, no PR is created. The workflow exits with an error. You will see the failure in the Actions tab.

If the entire run fails (OpenAI API error, configuration problem, etc.), no files are modified and no PR is created.

---

## API usage and cost

Each weekly run makes approximately:
- 1 research call (OpenAI with web search, ~$0.05-0.15)
- 3 article generation calls (GPT-4o, ~$0.10-0.20 per article)
- Up to 3 correction calls if em dashes are found (rare, ~$0.05-0.10 each)

Estimated total per week: $0.50-1.00 at current GPT-4o pricing.

The system has a hard limit of 3 articles per run. It cannot generate more than 3 articles in a single scheduled execution regardless of how it is configured.

---

## GitHub secret you need to add

Before the first live run, add your OpenAI API key to GitHub:

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `OPENAI_API_KEY`
5. Value: your OpenAI API key (starts with `sk-`)
6. Click **Add secret**

The automation will not run without this secret.

---

## Dry run procedure (before first live run)

1. Go to Actions → Weekly Article Generation → Run workflow
2. Check the **Dry run** box
3. Click Run workflow
4. Review the output in the Actions log
5. Check `content-system/_dryrun_*.html` files to see the generated article HTML
6. If satisfied, uncheck Dry run and run again — or wait for the next scheduled Sunday run
