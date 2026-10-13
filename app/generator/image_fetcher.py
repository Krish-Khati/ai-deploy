"""
Fetch a relevant cover image for a blog post.

Primary source is Pixabay (needs a free PIXABAY_API_KEY).
If that key is missing or Pixabay fails, we fall back to the Openverse API,
which needs no API key at all - so this works out of the box.

Every candidate URL is verified to actually serve an image before we return
it, because some hosts (Wikimedia, for example) reject non-browser clients.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
PIXABAY_URL = "https://pixabay.com/api/"
OPENVERSE_URL = "https://api.openverse.org/v1/images/"

# Some image hosts return 403/429 unless a browser-like User-Agent is sent.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ContentPlannerBot/1.0)"}
TIMEOUT = 20


def _pick_best(query, results, meta_keys):
    """
    Rank results by how many query words appear in their title/tags.

    Without this, search engines happily return something wildly unrelated
    (searching "coding" once returned an infrared remote control receiver).
    """
    words = [w for w in query.lower().split() if len(w) > 2]
    ranked = []

    for index, item in enumerate(results):
        meta = " ".join(str(item.get(k, "")) for k in meta_keys).lower()
        score = sum(1 for w in words if w in meta)
        ranked.append((score, -index, item))

    # Highest score first, original order preserved for ties
    ranked.sort(reverse=True)
    return [item for _, _, item in ranked]


def _is_usable_image(url):
    """Check the URL really serves an image before we hand it to dev.to."""
    if not url or not url.startswith("http"):
        return False

    try:
        response = requests.head(
            url, timeout=15, allow_redirects=True, headers=HEADERS
        )
        if response.status_code == 200 and (response.headers.get("Content-Type") or "").startswith("image"):
            return True

        # Some CDNs reject HEAD, so retry with a tiny ranged GET
        ranged = requests.get(
            url,
            timeout=15,
            headers={**HEADERS, "Range": "bytes=0-1024"},
            stream=True,
        )
        return ranged.status_code == 200 and (ranged.headers.get("Content-Type") or "").startswith("image")
    except requests.RequestException:
        return False


def _pixabay_candidates(query):
    """Return ranked image URLs from Pixabay, or an empty list."""
    if not PIXABAY_API_KEY:
        return []

    try:
        response = requests.get(
            PIXABAY_URL,
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "per_page": 3,
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            return []

        hits = response.json().get("hits", [])
        ranked = _pick_best(query, hits, ["tags", "tags_en"])
        return [hit.get("largeImageURL") for hit in ranked]
    except (requests.RequestException, ValueError):
        return []


def _openverse_candidates(query):
    """Return ranked image URLs from Openverse (no API key needed)."""
    try:
        response = requests.get(
            OPENVERSE_URL,
            params={"q": query, "page_size": 5, "license_type": "commercial"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            return []

        results = response.json().get("results", [])
        ranked = _pick_best(query, results, ["title", "tags"])
        return [item.get("url") for item in ranked]
    except (requests.RequestException, ValueError):
        return []


def get_relevant_image(query, fallback_queries=None):
    """
    Return a verified cover image URL for the given search query.

    Tries Pixabay first (if PIXABAY_API_KEY is set), then falls back to the
    keyless Openverse API. Each candidate is checked to make sure it really
    serves an image. Returns None if nothing usable is found, so callers
    can just continue without a cover image.

    Post titles are often metaphorical ("the illusion of good enough"), which
    makes for terrible image searches, so callers can pass fallback_queries
    to try once the main query comes up empty.
    """
    attempts = [query] + list(fallback_queries or [])

    for attempt in attempts:
        if not attempt or not attempt.strip():
            continue

        attempt = attempt.strip()

        candidates = _pixabay_candidates(attempt)
        if not candidates:
            candidates = _openverse_candidates(attempt)

        for url in candidates:
            if _is_usable_image(url):
                return url

    return None


if __name__ == "__main__":
    test_query = "software developer coding"
    print(f"Searching for an image: '{test_query}'")
    print(
        f"Pixabay key configured: "
        f"{'yes' if PIXABAY_API_KEY else 'no (using Openverse fallback)'}"
    )

    image_url = get_relevant_image(test_query)

    if image_url:
        print(f"Found image: {image_url}")
    else:
        print("No usable image found. The post will be published without a cover image.")
