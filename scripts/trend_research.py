"""
trend_research.py
Scans Google Custom Search (web + news mode), and RSS feeds for emerging
AI models, open-source tools, n8n workflows, and local LLM (Ollama) news.
Returns a de-duplicated, ranked list of topic dicts ready for repo generation.
"""

import os
import re
import time
import logging
import hashlib
from datetime import datetime, timezone

import requests
import feedparser

logger = logging.getLogger("trend_research")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")

SEARCH_QUERIES = [
    "new open source AI model release",
    "n8n workflow automation template",
    "Ollama local LLM new model",
    "AI automation tool launch",
    "new AI agent framework github",
]

RSS_FEEDS = [
    "https://huggingface.co/blog/feed.xml",
    "https://www.reddit.com/r/LocalLLaMA/.rss",
    "https://www.reddit.com/r/n8n/.rss",
    "https://ollama.com/blog/feed.xml",
    "https://github.blog/changelog/feed/",
]

STOPWORDS = {"the", "a", "an", "for", "with", "and", "to", "of", "in", "on", "is"}

CASUAL_TITLE_PATTERNS = [
    r"\bmy\s", r"\bi'm\b", r"\bi've\b", r"\bi\s", r"\bwe're\b", r"\bwe've\b",
    r"\bour\s", r"\bthanks\b", r"\bthank you\b", r"\bfiance", r"\bwife\b",
    r"\bhusband\b", r"\bask us anything\b", r"\bama\b", r"\bthis sub\b",
    r"\bregardless of what complaints\b", r"\bwe are the team\b",
]
_CASUAL_RE = re.compile("|".join(CASUAL_TITLE_PATTERNS), re.IGNORECASE)


def _is_technical_title(title: str) -> bool:
    """Rejects personal-anecdote / community-meta post titles (common on
    Reddit RSS) that read like forum chatter rather than a technical
    announcement — these produce unprofessional repo names and give small
    LLMs nothing factual to ground content on, leading to fabricated
    'explanations' of what the post is actually about."""
    return not _CASUAL_RE.search(title)


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60].strip("-")


def _topic_id(title: str) -> str:
    return hashlib.sha256(title.strip().lower().encode("utf-8")).hexdigest()[:12]


def fetch_google_results(query: str, num: int = 5) -> list[dict]:
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        logger.warning("Google API credentials missing, skipping query: %s", query)
        return []

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query,
        "num": min(num, 10),
        "dateRestrict": "d7",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("Google search failed for '%s': %s", query, exc)
        return []

    results = []
    for item in data.get("items", []):
        results.append(
            {
                "title": item.get("title", "").strip(),
                "snippet": item.get("snippet", "").strip(),
                "link": item.get("link", ""),
                "source": "google_search",
            }
        )
    return results


def fetch_rss_results(feed_url: str, limit: int = 5) -> list[dict]:
    results = []
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as exc:
        logger.error("RSS parse failed for %s: %s", feed_url, exc)
        return results

    for entry in parsed.entries[:limit]:
        results.append(
            {
                "title": getattr(entry, "title", "").strip(),
                "snippet": getattr(entry, "summary", "")[:280].strip(),
                "link": getattr(entry, "link", ""),
                "source": feed_url,
            }
        )
    return results


def collect_raw_candidates() -> list[dict]:
    candidates: list[dict] = []

    for query in SEARCH_QUERIES:
        candidates.extend(fetch_google_results(query))
        time.sleep(1)

    for feed_url in RSS_FEEDS:
        candidates.extend(fetch_rss_results(feed_url))

    return candidates


def dedupe_and_rank(candidates: list[dict], max_topics: int = 5) -> list[dict]:
    seen_ids = set()
    deduped = []

    for c in candidates:
        title = c.get("title", "")
        if not title or len(title) < 8:
            continue
        if not _is_technical_title(title):
            continue
        tid = _topic_id(title)
        if tid in seen_ids:
            continue
        seen_ids.add(tid)
        c["id"] = tid
        c["slug"] = _slugify(title)
        c["fetched_at"] = datetime.now(timezone.utc).isoformat()
        deduped.append(c)

    # simple ranking: prefer entries with longer, keyword-rich snippets
    def score(item: dict) -> int:
        text = (item.get("title", "") + " " + item.get("snippet", "")).lower()
        keywords = ["model", "open source", "ollama", "n8n", "agent", "automation", "llm"]
        return sum(text.count(k) for k in keywords) + len(item.get("snippet", "")) // 50

    deduped.sort(key=score, reverse=True)
    return deduped[:max_topics]


def get_daily_topics(max_topics: int = 5) -> list[dict]:
    raw = collect_raw_candidates()
    topics = dedupe_and_rank(raw, max_topics=max_topics)
    logger.info("Selected %d topics for today", len(topics))
    return topics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for t in get_daily_topics():
        print(t["title"], "->", t["link"])
