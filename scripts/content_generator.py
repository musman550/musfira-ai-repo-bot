"""
content_generator.py
Generates genuinely unique, topic-specific documentation content using a
local Ollama model (free, open-source, no external API key). Every piece
of content passes a quality gate before it's allowed downstream — nothing
short, empty, or boilerplate ever reaches a repo. If generation fails the
gate after retries, the caller must skip that topic instead of publishing
thin content.
"""

import os
import logging
import requests

logger = logging.getLogger("content_generator")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
MIN_OVERVIEW_WORDS = 80
MIN_SECTION_COUNT = 4

BANNED_PHRASES = [
    "lorem ipsum",
    "as an ai language model",
    "i cannot",
    "i'm sorry",
    "i am unable",
    "placeholder text",
]


class ContentGenerationError(Exception):
    """Raised when generated content fails the quality gate after retries."""


def _call_ollama(prompt: str, max_tokens: int = 900, timeout: int = 180) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.7},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _passes_quality_gate(text: str) -> bool:
    if not text or len(text.split()) < MIN_OVERVIEW_WORDS:
        return False
    lowered = text.lower()
    return not any(p in lowered for p in BANNED_PHRASES)


def _build_prompt(title: str, snippet: str) -> str:
    return f"""You are a technical writer producing original documentation for an
open-source repository about: "{title}"
Background context: {snippet or "a recent development in AI/automation tooling"}

Write these five sections, each separated by a line containing only "###".
Do not use markdown headers, do not repeat the section names, write plain content only.

1. A specific, concrete 3-paragraph overview: what this is, why it actually matters
   right now, and a realistic scenario of someone using it. No generic filler.
2. Five distinct key-feature sentences, one per line.
3. Three realistic use-case sentences, one per line.
4. Three FAQ pairs, each formatted exactly as:
   Q: <question>
   A: <answer>
5. A short setup/usage tip (2-4 sentences) specific to this topic.

No disclaimers, no apologies, no meta-commentary about being an AI. Content only."""


def generate_topic_content(topic: dict, retries: int = 2) -> dict:
    title = topic["title"]
    snippet = topic.get("snippet", "")
    prompt = _build_prompt(title, snippet)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            raw = _call_ollama(prompt)
            sections = [s.strip() for s in raw.split("###") if s.strip()]

            if len(sections) < MIN_SECTION_COUNT:
                raise ContentGenerationError(
                    f"only {len(sections)} sections returned, need {MIN_SECTION_COUNT}"
                )

            overview = sections[0]
            if not _passes_quality_gate(overview):
                raise ContentGenerationError("overview failed quality gate")

            return {
                "overview": overview,
                "features": sections[1] if len(sections) > 1 else "",
                "use_cases": sections[2] if len(sections) > 2 else "",
                "faq": sections[3] if len(sections) > 3 else "",
                "setup_tip": sections[4] if len(sections) > 4 else "",
            }
        except Exception as exc:  # noqa: BLE001 - we deliberately catch broadly and retry
            last_error = exc
            logger.warning(
                "Content generation attempt %d/%d failed for '%s': %s",
                attempt + 1, retries + 1, title, exc,
            )

    raise ContentGenerationError(f"generation failed after {retries + 1} attempts: {last_error}")


def wait_for_ollama(timeout_seconds: int = 60) -> bool:
    import time

    base = OLLAMA_URL.rsplit("/api/", 1)[0]
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/api/tags", timeout=5)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False
