"""
orchestrator.py
Daily entry point: research trends, generate unique deep-dive content per
topic via rotating local Ollama models, and publish repos until the daily
target is met — retrying with fresh candidates as topics get skipped, so a
handful of skips (dedup/quality/validation) doesn't leave the day short.
A failure on one topic is logged and skipped; it never blocks the rest of
the run and never results in a thin or broken repo.
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
from github_publisher import publish_repo_bundle, upload_file
from content_generator import generate_topic_content, ContentGenerationError, wait_for_ollama
from dedup_state import load_state, save_state, is_duplicate, mark_published
from license_builder import build_license
from code_validator import validate_files, ValidationError
from hub_builder import build_hub_readme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

MIN_REPOS = int(os.environ.get("REPOS_PER_DAY_MIN", 2))
MAX_REPOS = int(os.environ.get("REPOS_PER_DAY_MAX", 5))
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
INFRA_REPO = os.environ.get("INFRA_REPO", "musfira-ai-repo-bot")
# safety cap so a bad day can't loop forever burning API quota / runner time
MAX_CANDIDATES_TOTAL = int(os.environ.get("MAX_CANDIDATES_TOTAL", 40))


def build_repo_name(topic: dict) -> str:
    return f"musfira-ai-{topic['slug']}"[:100]


def build_topics_list(topic: dict) -> list[str]:
    base = ["musfira-ai", "ai-automation", "n8n", "ollama", "open-source-ai"]
    extra = topic["slug"].split("-")[:5]
    return list(dict.fromkeys(base + extra))


def try_publish_topic(topic: dict, state: dict) -> bool:
    """Returns True if this topic was successfully published."""
    if is_duplicate(state, topic["title"], topic.get("snippet", "")):
        logger.info("Skipping near-duplicate topic: %s", topic["title"])
        return False

    try:
        generated = generate_topic_content(topic)
    except ContentGenerationError as exc:
        logger.warning("Content generation failed for '%s', skipping: %s", topic["title"], exc)
        return False

    repo_name = build_repo_name(topic)
    readme = build_readme(topic, generated)

    files = {
        "README.md": readme,
        "main.py": build_main_py(topic),
        "requirements.txt": build_requirements_txt(),
        "workflow.json": build_workflow_json(topic),
        "ui/index.html": build_chat_ui_html(topic),
        "LICENSE": build_license(),
    }

    try:
        validate_files(files)
    except ValidationError as exc:
        logger.error("Validation failed for '%s', skipping (not published): %s", topic["title"], exc)
        return False

    description = generated["overview"].split(".")[0].strip()[:350]
    ok = publish_repo_bundle(
        repo_name=repo_name,
        files=files,
        description=description,
        topics=build_topics_list(topic),
    )

    if not ok:
        logger.error("Publish failed for %s, skipping (not marked as published).", repo_name)
        return False

    mark_published(state, topic["title"], generated["overview"], repo_name)
    logger.info("Published repo: %s (model: %s)", repo_name, generated.get("generated_by", "?"))
    return True


def update_hub(state: dict) -> None:
    try:
        hub_readme = build_hub_readme(state["published"], GITHUB_USERNAME)
        upload_file(INFRA_REPO, "README.md", hub_readme, "Update hub index")
        upload_file(INFRA_REPO, "LICENSE", build_license(), "Ensure MIT LICENSE present")
    except Exception as exc:  # noqa: BLE001 - hub update is best-effort, never fatal
        logger.warning("Hub index update failed (non-fatal): %s", exc)


def run() -> None:
    target_count = random.randint(MIN_REPOS, MAX_REPOS)
    logger.info("Target repos for today: %d", target_count)

    if not wait_for_ollama(timeout_seconds=90):
        logger.error("Ollama server not reachable — aborting run rather than publishing thin content.")
        return

    state = load_state()
    published = 0

    logger.info("Fetching candidate pool (up to %d topics)...", MAX_CANDIDATES_TOTAL)
    candidates = get_daily_topics(max_topics=MAX_CANDIDATES_TOTAL)

    if not candidates:
        logger.warning("No topics found today, nothing to publish.")
        return

    for topic in candidates:
        if published >= target_count:
            break
        try:
            if try_publish_topic(topic, state):
                published += 1
        except Exception as exc:  # noqa: BLE001 - never let one bad topic kill the run
            logger.error("Unexpected error on topic '%s', skipping: %s", topic["title"], exc)
            continue

    if published > 0:
        save_state(state)
        update_hub(state)

    if published < target_count:
        logger.warning(
            "Only %d/%d repos published after trying %d candidates (pool exhausted or safety cap).",
            published, target_count, len(candidates),
        )
    logger.info("Done. %d repos published today (target was %d).", published, target_count)


if __name__ == "__main__":
    run()
