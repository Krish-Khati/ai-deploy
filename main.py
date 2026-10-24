"""Entry point: GitHub activity -> Groq blog post -> dev.to draft."""

from app.brain.decision_engine import run

if __name__ == "__main__":
    run()
