"""Look up the content theme for a day from the festival calendar."""

import json
import os
from datetime import date

CALENDAR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "festival_calendar.json"
)


def get_todays_theme(today=None):
    """Return today's theme, or None if today is not a special day."""
    day = today or date.today()
    with open(CALENDAR_PATH, encoding="utf-8") as f:
        calendar = json.load(f)
    return calendar.get(day.isoformat())


if __name__ == "__main__":
    theme = get_todays_theme()
    print(theme or "No special theme today")
