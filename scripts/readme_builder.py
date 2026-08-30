"""
readme_builder.py
Builds SEO/GEO/EEO-optimized README.md content for a generated repository.
"""

import os
from datetime import datetime, timezone

YOUTUBE_CHANNEL_URL = os.environ.get(
    "YOUTUBE_CHANNEL_URL", "https://www.youtube.com/@automatewithmusfiraai"
)
WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://musfiraai.com")
LINKEDIN_URL = os.environ.get("LINKEDIN_URL", "https://www.linkedin.com/in/musfira-ai-b3218b39b")
INSTAGRAM_URL = os.environ.get("INSTAGRAM_URL", "https://instagram.com/musma_n55")
GMAPS_URL = os.environ.get("GMAPS_URL", "https://share.google/kJchUsfQyABVLghSF")
WHATSAPP_URL = os.environ.get("WHATSAPP_URL", "https://wa.me/923217358096")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER", "+923217358096")


def _promo_block() -> str:
    links = [
        f"- 🌐 Website: [{WEBSITE_URL}]({WEBSITE_URL})",
        f"- ▶️ YouTube: [Automate With Musfira AI]({YOUTUBE_CHANNEL_URL})",
        f"- 💼 LinkedIn: [{LINKEDIN_URL}]({LINKEDIN_URL})",
        f"- 📸 Instagram: [{INSTAGRAM_URL}]({INSTAGRAM_URL})",
        f"- 📍 Location: [Google Maps]({GMAPS_URL})",
        f"- 💬 WhatsApp: [Chat with us]({WHATSAPP_URL})",
        f"- 📞 Call: [{PHONE_NUMBER}](tel:{PHONE_NUMBER})",
    ]
    return "\n".join(links)


def build_readme(topic: dict, generated: dict) -> str:
    """
    generated must come from content_generator.generate_topic_content() and
    have already passed its quality gate — this function does not fall back
    to thin placeholder text. Callers must skip publishing if generation
    failed rather than calling this with empty content.
    """
    title = topic["title"]
    link = topic.get("link", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    features = generated.get("features", "")
    use_cases = generated.get("use_cases", "")
    faq = generated.get("faq", "")
    setup_tip = generated.get("setup_tip", "")

    return f"""# Musfira AI {title} - By Musfira AI

> Curated, written, and published by **Musfira AI**.

## Overview

{generated["overview"]}

**Source reference:** [{link}]({link})
**Published:** {today}

## Key Features

{features}

## Use Cases

{use_cases}

## Quickstart

### Python

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

### n8n Workflow

Import `workflow.json` into your n8n instance via **Workflows > Import from File**.

### Local LLM (Ollama)

```bash
ollama pull llama3
ollama run llama3
```

{setup_tip}

## FAQ

{faq}

## Repository Structure

```
.
├── main.py
├── requirements.txt
├── workflow.json
├── ui/
│   └── index.html
└── README.md
```

## About Musfira AI

Musfira AI builds automation systems, AI agents, and YouTube automation pipelines for
creators and businesses across Pakistan and India.

{_promo_block()}

---

*This repository is part of Musfira AI's daily AI trend tracking series. Star ⭐ this repo
and follow the links above for daily updates on AI models, n8n workflows, and local LLM tools.*
"""


if __name__ == "__main__":
    sample_topic = {
        "title": "Sample Open Source LLM",
        "link": "https://example.com",
    }
    sample_generated = {
        "overview": "This is a placeholder overview for local testing only.",
        "features": "- Example feature one\n- Example feature two",
        "use_cases": "- Example use case one",
        "faq": "Q: Is this real?\nA: This is a local test fixture.",
        "setup_tip": "Run `ollama serve` locally before testing this module.",
    }
    print(build_readme(sample_topic, sample_generated))
