# Content Planner Automation

Reads the latest commit from a GitHub repo, writes a 200-300 word first-person post with Groq,
checks it meets a minimum quality bar, finds a cover image, and creates a **draft** on dev.to
for manual review. A GitHub Action runs it daily at 09:00 IST.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in the keys
```

`.env` keys:

| Key | Required | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | yes | Writes the post |
| `DEVTO_API_KEY` | yes | Creates the draft |
| `GITHUB_TOKEN` | no | Avoids GitHub API rate limits |
| `PIXABAY_API_KEY` | no | Preferred cover images; falls back to Openverse (no key needed) |

## Run

```powershell
python main.py
```

`python app/brain/decision_engine.py` does the same thing, and is what the GitHub Action calls.

The target repo is currently hard-coded to `Krish-Khati/ai-deploy` in `app/brain/decision_engine.py`.

## What actually works

- `app/brain/github_watcher.py` - latest commit and release for a repo
- `app/brain/decision_engine.py` - post generation, quality gate, image query, pipeline
- `app/generator/image_fetcher.py` - Pixabay, then keyless Openverse fallback
- `app/connectors/devto_connector.py` - dev.to draft creation

## Planned but not implemented

These files exist as empty placeholders: LinkedIn and Instagram connectors, GitHub connector,
trend analyzer, SEO optimizer, caption writer, blog writer module, calendar events, festival
calendar, and `app/config/settings.py`. Nothing imports them yet.
