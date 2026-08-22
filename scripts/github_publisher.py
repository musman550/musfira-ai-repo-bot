"""
github_publisher.py
Creates and configures a public GitHub repository via the REST API, then
pushes the generated README, starter code, workflow.json, and UI files
using the Git Data API (no local git binary required).
"""

import os
import base64
import logging
import time

import requests

logger = logging.getLogger("github_publisher")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
API_ROOT = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _check_repo_exists(repo_name: str) -> bool:
    resp = requests.get(
        f"{API_ROOT}/repos/{GITHUB_USERNAME}/{repo_name}", headers=HEADERS, timeout=15
    )
    return resp.status_code == 200


def create_repository(repo_name: str, description: str, topics: list[str]) -> dict | None:
    if _check_repo_exists(repo_name):
        logger.info("Repo %s already exists, skipping creation", repo_name)
        return None

    payload = {
        "name": repo_name,
        "description": description[:350],
        "private": False,
        "has_issues": True,
        "has_projects": False,
        "has_wiki": False,
        "auto_init": True,
    }

    resp = requests.post(f"{API_ROOT}/user/repos", headers=HEADERS, json=payload, timeout=15)
    if resp.status_code not in (200, 201):
        logger.error("Repo creation failed for %s: %s %s", repo_name, resp.status_code, resp.text)
        return None

    repo_data = resp.json()

    # topics endpoint requires a distinct Accept header + separate call
    topics_resp = requests.put(
        f"{API_ROOT}/repos/{GITHUB_USERNAME}/{repo_name}/topics",
        headers={**HEADERS, "Accept": "application/vnd.github.mercy-preview+json"},
        json={"names": [t.lower().replace(" ", "-") for t in topics][:20]},
        timeout=15,
    )
    if topics_resp.status_code != 200:
        logger.warning("Topic assignment failed for %s: %s", repo_name, topics_resp.text)

    return repo_data


def _get_file_sha(repo_name: str, path: str) -> str | None:
    resp = requests.get(
        f"{API_ROOT}/repos/{GITHUB_USERNAME}/{repo_name}/contents/{path}",
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def upload_file(repo_name: str, path: str, content: str, message: str) -> bool:
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": encoded, "branch": "main"}

    existing_sha = _get_file_sha(repo_name, path)
    if existing_sha:
        payload["sha"] = existing_sha

    resp = requests.put(
        f"{API_ROOT}/repos/{GITHUB_USERNAME}/{repo_name}/contents/{path}",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        logger.error("File upload failed for %s/%s: %s", repo_name, path, resp.text)
        return False
    return True


def publish_repo_bundle(repo_name: str, files: dict[str, str], description: str, topics: list[str]) -> bool:
    """
    files: mapping of relative path -> file content string
    """
    repo_data = create_repository(repo_name, description, topics)
    if repo_data is None and not _check_repo_exists(repo_name):
        return False

    # auto_init creates a default README; wait briefly for it to settle
    time.sleep(2)

    ok = True
    for path, content in files.items():
        success = upload_file(repo_name, path, content, message=f"Musfira AI: add {path}")
        ok = ok and success
        time.sleep(0.5)

    return ok
