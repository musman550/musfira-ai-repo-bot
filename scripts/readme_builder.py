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


def _promo_block() -> str:
    links = [
        f"- 🌐 Website: [{WEBSITE_URL}]({WEBSITE_URL})",
        f"- ▶️ YouTube: [Automate With Musfira AI]({YOUTUBE_CHANNEL_URL})",
        f"- 💼 LinkedIn: [{LINKEDIN_URL}]({LINKEDIN_URL})",
        f"- 📸 Instagram: [{INSTAGRAM_URL}]({INSTAGRAM_URL})",
        f"- 📍 Location: [Google Maps]({GMAPS_URL})",
    ]
    return "\n".join(links)


def build_readme(topic: dict) -> str:
    title = topic["title"]
    snippet = topic.get("snippet", "")
    link = topic.get("link", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""# Musfira AI {title} - By Musfira AI

> Daily AI trend digest and automation starter kit, curated and published by **Musfira AI**.

## Overview

{snippet or "Curated notes, setup guide, and starter code for this trending AI development."}

**Source reference:** [{link}]({link})
**Published:** {today}

## What's Inside

- Summary of the trend/tool and why it matters
- Quickstart setup guide (Python + n8n where applicable)
- Local/edge execution config (Ollama-ready)
- Lightweight HTML/Tailwind chat UI starter (where applicable)

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
    sample = {
        "title": "Sample Open Source LLM",
        "snippet": "A new lightweight open-source LLM released for local inference.",
        "link": "https://example.com",
    }
    print(build_readme(sample))
