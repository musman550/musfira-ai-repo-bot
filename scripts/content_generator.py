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
OLLAMA_MODELS = [
    m.strip()
    for m in os.environ.get("OLLAMA_MODELS", "llama3.2:1b,qwen2.5:1.5b,gemma2:2b").split(",")
    if m.strip()
]
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


def _call_ollama(prompt: str, model: str, max_tokens: int = 900, timeout: int = 180) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
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


LEAKED_INSTRUCTION_PATTERNS = [
    "specific, concrete 3-paragraph overview",
    "distinct key-feature sentences",
    "realistic use-case sentences",
    "faq pairs",
    "setup/usage tip",
    "no disclaimers, no apologies",
    "three paragraphs explaining what this is",
    "five sentences, one per line",
    "three sentences, one per line",
    "question-answer pairs formatted as",
    "practical setup or usage tip",
    "begin your response with",
    "block 1", "block 2", "block 3", "block 4", "block 5",
]
BARE_HEADER_LINES = {"overview", "key features", "use cases", "faq", "setup tip", "features"}


def _strip_leaked_instructions(text: str) -> str:
    """Small models sometimes echo the prompt's instruction wording, or a bare
    section header, as a leading line. Strip any line matching those patterns
    so it never reaches a published README."""
    cleaned_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        lowered = stripped.lower().strip(":.- ")
        if lowered in BARE_HEADER_LINES:
            continue
        if any(pat in lowered for pat in LEAKED_INSTRUCTION_PATTERNS):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _build_prompt(title: str, snippet: str) -> str:
    return f"""Write original technical documentation about: "{title}"
Context: {snippet or "a recent development in AI/automation tooling"}

Output exactly 5 blocks of content separated by a line containing only ###.
Start writing the actual content immediately in each block — do not restate
these instructions, do not print section titles or numbers, do not print
words like "Overview" or "Key Features" as a heading.

Block 1: Three paragraphs explaining what this is, why it matters right now,
and a concrete scenario of someone using it.
Block 2: Five sentences, one per line, each describing one capability.
Block 3: Three sentences, one per line, each describing a real-world use case.
Block 4: Three question-answer pairs formatted as:
Q: <question>
A: <answer>
Block 5: Two to four sentences with a practical setup or usage tip.

Begin your response with the Block 1 content directly, no preamble."""


def generate_topic_content(topic: dict, retries: int | None = None) -> dict:
    title = topic["title"]
    snippet = topic.get("snippet", "")
    prompt = _build_prompt(title, snippet)

    if retries is None:
        retries = len(OLLAMA_MODELS) - 1  # try every available model before giving up

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        model = OLLAMA_MODELS[attempt % len(OLLAMA_MODELS)]
        try:
            raw = _call_ollama(prompt, model=model)
            sections = [s.strip() for s in raw.split("###") if s.strip()]
            sections = [_strip_leaked_instructions(s) for s in sections]
            sections = [s for s in sections if s]  # drop any section emptied by cleaning

            if len(sections) < MIN_SECTION_COUNT:
                raise ContentGenerationError(
                    f"only {len(sections)} usable sections after cleaning, need {MIN_SECTION_COUNT}"
                )

            overview = sections[0]
            if not _passes_quality_gate(overview):
                raise ContentGenerationError("overview failed quality gate after cleaning")

            return {
                "overview": overview,
                "features": sections[1] if len(sections) > 1 else "",
                "use_cases": sections[2] if len(sections) > 2 else "",
                "faq": sections[3] if len(sections) > 3 else "",
                "setup_tip": sections[4] if len(sections) > 4 else "",
                "generated_by": model,
            }
        except Exception as exc:  # noqa: BLE001 - we deliberately catch broadly and retry
            last_error = exc
            logger.warning(
                "Content generation attempt %d/%d (model=%s) failed for '%s': %s",
                attempt + 1, retries + 1, model, title, exc,
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
