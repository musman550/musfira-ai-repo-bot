"""
hub_builder.py
Builds a directory/index README for the infra repo itself, listing every
published repo so visitors (and Google) can browse the full catalog from
one place — this is the internal-linking hub that gives the daily repos
real cross-linked structure instead of being isolated pages.
"""

from datetime import datetime, timezone


def build_hub_readme(published: dict, github_username: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not published:
        repo_list = "_No repos published yet — check back soon._"
    else:
        rows = []
        for entry in sorted(published.values(), key=lambda e: e.get("repo", "")):
            repo = entry.get("repo", "")
            title = entry.get("title", repo)
            rows.append(f"- [{title}](https://github.com/{github_username}/{repo})")
        repo_list = "\n".join(rows)

    return f"""# Musfira AI — Daily Repo Bot

> The automation engine that researches AI/automation trends daily and
> publishes a fully documented, MIT-licensed starter repo for each one.

**Total repos published:** {len(published)}
**Last updated:** {today}

## Catalog

{repo_list}

## How it works

Every day this bot:
1. Scans GitHub, Hugging Face, Reddit (r/LocalLLaMA, r/n8n), and Ollama's blog for trending AI/automation topics.
2. Generates unique, original documentation for each topic using local open-source models (Ollama).
3. Publishes a complete starter repo: README, Python starter script, n8n workflow, a local chat UI, and an MIT LICENSE.
4. Skips anything that fails a content quality or duplicate-content check — nothing thin or broken gets published.

## Links

- 🌐 Website: [musfiraai.com](https://musfiraai.com)
- ▶️ YouTube: [Automate With Musfira AI](https://www.youtube.com/@automatewithmusfiraai)
- 💼 LinkedIn: [Musfira AI](https://www.linkedin.com/in/musfira-ai-b3218b39b)
- 📸 Instagram: [@musma_n55](https://instagram.com/musma_n55)
- 💬 WhatsApp: [Chat with us](https://wa.me/923217358096)
- 📞 Call: [+923217358096](tel:+923217358096)

## License

This project is licensed under the [MIT License](LICENSE).
"""
