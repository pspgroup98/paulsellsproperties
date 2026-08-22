"""Central configuration loader for the editorial automation system."""
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH               = REPO_ROOT / "content-system" / "config.json"
ARTICLE_INDEX_PATH        = REPO_ROOT / "content-system" / "article-index.json"
MANUAL_TOPICS_PATH        = REPO_ROOT / "content-system" / "manual-topics.json"
EDITORIAL_GUIDELINES_PATH = REPO_ROOT / "content-system" / "EDITORIAL_GUIDELINES.md"
BLOG_DIR                  = REPO_ROOT / "blog"
SITEMAP_PATH              = REPO_ROOT / "sitemap.xml"
RSS_PATH                  = REPO_ROOT / "feed.xml"
BLOG_INDEX_PATH           = REPO_ROOT / "blog" / "index.html"
HOMEPAGE_PATH             = REPO_ROOT / "index.html"

# ── Phase 3: ChatGPT editorial bridge paths ──────────────────────────────────
BACKLOG_PATH           = REPO_ROOT / "content-system" / "editorial-backlog.json"
WATCH_LIST_PATH        = REPO_ROOT / "content-system" / "editorial-watch-list.json"
APPROVED_BATCHES_DIR   = REPO_ROOT / "content-system" / "approved-batches"
EDITORIAL_CONTEXT_PATH = REPO_ROOT / "content-system" / "editorial-context.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    # Environment variable overrides
    cfg["writing_model"]   = os.environ.get("OPENAI_MODEL",          cfg.get("writing_model",   "gpt-4o"))
    cfg["research_model"]  = os.environ.get("OPENAI_RESEARCH_MODEL", cfg.get("research_model",  "gpt-4o"))
    return cfg


def load_article_index() -> list:
    if ARTICLE_INDEX_PATH.exists():
        with open(ARTICLE_INDEX_PATH) as f:
            return json.load(f)
    return []


def load_manual_topics() -> list:
    if MANUAL_TOPICS_PATH.exists():
        with open(MANUAL_TOPICS_PATH) as f:
            data = json.load(f)
        return data.get("topics", [])
    return []


def consume_manual_topics(used_count: int) -> None:
    """Remove the first `used_count` topics from the manual topics file."""
    if not MANUAL_TOPICS_PATH.exists():
        return
    with open(MANUAL_TOPICS_PATH) as f:
        data = json.load(f)
    data["topics"] = data.get("topics", [])[used_count:]
    with open(MANUAL_TOPICS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_editorial_guidelines() -> str:
    with open(EDITORIAL_GUIDELINES_PATH) as f:
        return f.read()


def load_backlog() -> dict:
    """Load the editorial backlog, returning a default empty structure if absent."""
    if BACKLOG_PATH.exists():
        with open(BACKLOG_PATH) as f:
            return json.load(f)
    return {
        "_schema": "1",
        "_description": "Topics considered but not selected. Reviewed each week before new topic selection.",
        "entries": [],
    }


def load_watch_list() -> dict:
    """Load the editorial watch list, returning a default empty structure if absent."""
    if WATCH_LIST_PATH.exists():
        with open(WATCH_LIST_PATH) as f:
            return json.load(f)
    return {
        "_schema": "1",
        "_description": "Developing stories to monitor. Reviewed each week in the research phase.",
        "entries": [],
    }
