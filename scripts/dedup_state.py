"""
dedup_state.py
Tracks previously published topic titles/content hashes inside a state
file (state/published.json) committed to the infra repo itself, so the
same topic or near-duplicate content never gets published twice across
days.
"""

import os
import json
import base64
import hashlib
import logging

import requests

logger = logging.getLogger("dedup_state")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
INFRA_REPO = os.environ.get("INFRA_REPO", "musfira-ai-repo-bot")
STATE_PATH = "state/published.json"
API_ROOT = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def _content_hash(title: str, overview: str) -> str:
    combined = (title.strip().lower() + "|" + overview.strip().lower())[:2000]
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


def load_state() -> dict:
    url = f"{API_ROOT}/repos/{GITHUB_USERNAME}/{INFRA_REPO}/contents/{STATE_PATH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return {"published": {}, "sha": None}

    data = resp.json()
    try:
        decoded = base64.b64decode(data["content"]).decode("utf-8")
        published = json.loads(decoded)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Could not parse existing state file, starting fresh: %s", exc)
        published = {}

    return {"published": published, "sha": data.get("sha")}


def save_state(state: dict) -> bool:
    url = f"{API_ROOT}/repos/{GITHUB_USERNAME}/{INFRA_REPO}/contents/{STATE_PATH}"
    encoded = base64.b64encode(
        json.dumps(state["published"], indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Update published-topics dedup state",
        "content": encoded,
        "branch": "main",
    }
    if state.get("sha"):
        payload["sha"] = state["sha"]

    resp = requests.put(url, headers=HEADERS, json=payload, timeout=15)
    if resp.status_code not in (200, 201):
        logger.error("Failed to save dedup state: %s", resp.text)
        return False
    return True


def is_duplicate(state: dict, title: str, overview: str) -> bool:
    h = _content_hash(title, overview)
    return h in state["published"]


def mark_published(state: dict, title: str, overview: str, repo_name: str) -> None:
    h = _content_hash(title, overview)
    state["published"][h] = {"title": title, "repo": repo_name}
