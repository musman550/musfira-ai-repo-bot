"""
orchestrator.py
Daily entry point: research trends, generate 2-5 repos, publish each with
README, starter code, n8n workflow, and a Tailwind chat UI.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")

MIN_REPOS = int(os.environ.get("REPOS_PER_DAY_MIN", 2))
MAX_REPOS = int(os.environ.get("REPOS_PER_DAY_MAX", 5))


def build_repo_name(topic: dict) -> str:
    return f"musfira-ai-{topic['slug']}"[:100]


def build_topics_list(topic: dict) -> list[str]:
    base = ["musfira-ai", "ai-automation", "n8n", "ollama", "open-source-ai"]
    extra = topic["slug"].split("-")[:5]
    return list(dict.fromkeys(base + extra))


def run() -> None:
    target_count = random.randint(MIN_REPOS, MAX_REPOS)
    logger.info("Target repos for today: %d", target_count)

    topics = get_daily_topics(max_topics=target_count)
    if not topics:
        logger.warning("No topics found today, nothing to publish.")
        return

    published = 0
    for topic in topics:
        repo_name = build_repo_name(topic)
        readme = build_readme(topic)

        files = {
            "README.md": readme,
            "main.py": build_main_py(topic),
            "requirements.txt": build_requirements_txt(),
            "workflow.json": build_workflow_json(topic),
            "ui/index.html": build_chat_ui_html(topic),
        }

        description = f"Musfira AI daily digest: {topic['title']}"[:350]
        ok = publish_repo_bundle(
            repo_name=repo_name,
            files=files,
            description=description,
            topics=build_topics_list(topic),
        )

        if ok:
            published += 1
            logger.info("Published repo: %s", repo_name)
        else:
            logger.error("Failed to publish repo: %s", repo_name)

    logger.info("Done. %d/%d repos published today.", published, len(topics))


if __name__ == "__main__":
    run()
