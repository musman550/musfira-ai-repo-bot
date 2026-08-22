"""
orchestrator.py
Daily entry point: research trends, generate unique deep-dive content per
topic via a local Ollama model, and publish 2-5 repos — but ONLY topics
that pass the content quality gate and aren't near-duplicates of anything
already published. A failure on one topic is logged and skipped; it never
blocks the rest of the run and never results in a thin or broken repo.
"""

import os
import logging
import random

from trend_research import get_daily_topics
from readme_builder import build_readme
from starter_templates import (
    build_main_py,
    build_requirements_txt,
    build_workflow_json,
    build_chat_ui_html,
)
from github_publisher import publish_repo_bundle
from content_generator import generate_topic_content, ContentGenerationError, wait_for_ollama
from dedup_state import load_state, save_state, is_duplicate, mark_published

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

MIN_REPOS = int(os.environ.get("REPOS_PER_DAY_MIN", 2))
MAX_REPOS = int(os.environ.get("REPOS_PER_DAY_MAX", 5))
# fetch more candidates than needed, since some will be skipped (dedup/quality)
CANDIDATE_MULTIPLIER = 3


def build_repo_name(topic: dict) -> str:
    return f"musfira-ai-{topic['slug']}"[:100]


def build_topics_list(topic: dict) -> list[str]:
    base = ["musfira-ai", "ai-automation", "n8n", "ollama", "open-source-ai"]
    extra = topic["slug"].split("-")[:5]
    return list(dict.fromkeys(base + extra))


def run() -> None:
    target_count = random.randint(MIN_REPOS, MAX_REPOS)
    logger.info("Target repos for today: %d", target_count)

    if not wait_for_ollama(timeout_seconds=90):
        logger.error("Ollama server not reachable — aborting run rather than publishing thin content.")
        return

    candidates = get_daily_topics(max_topics=target_count * CANDIDATE_MULTIPLIER)
    if not candidates:
        logger.warning("No topics found today, nothing to publish.")
        return

    state = load_state()
    published = 0

    for topic in candidates:
        if published >= target_count:
            break

        try:
            if is_duplicate(state, topic["title"], topic.get("snippet", "")):
                logger.info("Skipping near-duplicate topic: %s", topic["title"])
                continue

            generated = generate_topic_content(topic, retries=2)

            if is_duplicate(state, topic["title"], generated["overview"]):
                logger.info("Skipping topic with duplicate generated overview: %s", topic["title"])
                continue

            repo_name = build_repo_name(topic)
            readme = build_readme(topic, generated)

            files = {
                "README.md": readme,
                "main.py": build_main_py(topic),
                "requirements.txt": build_requirements_txt(),
                "workflow.json": build_workflow_json(topic),
                "ui/index.html": build_chat_ui_html(topic),
            }

            description = generated["overview"].split(".")[0].strip()[:350]
            ok = publish_repo_bundle(
                repo_name=repo_name,
                files=files,
                description=description,
                topics=build_topics_list(topic),
            )

            if not ok:
                logger.error("Publish failed for %s, skipping (not marked as published).", repo_name)
                continue

            mark_published(state, topic["title"], generated["overview"], repo_name)
            published += 1
            logger.info("Published repo: %s", repo_name)

        except ContentGenerationError as exc:
            logger.warning("Content generation failed for '%s', skipping: %s", topic["title"], exc)
            continue
        except Exception as exc:  # noqa: BLE001 - never let one bad topic kill the whole run
            logger.error("Unexpected error on topic '%s', skipping: %s", topic["title"], exc)
            continue

    if published > 0:
        save_state(state)

    logger.info("Done. %d repos published today (target was %d).", published, target_count)


if __name__ == "__main__":
    run()
