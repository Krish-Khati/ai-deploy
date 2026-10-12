import os
import requests
from dotenv import load_dotenv

load_dotenv()

DEVTO_API_KEY = os.getenv("DEVTO_API_KEY")
API_URL = "https://dev.to/api/articles"
HEADERS = {
    "api-key": DEVTO_API_KEY,
    "Content-Type": "application/json"
}


def post_to_devto(title, body_markdown, tags=None, published=False):
    """
    Post an article to dev.to API.

    Args:
        title (str): Article title
        body_markdown (str): Article body in Markdown format
        tags (list): List of tags (max 4)
        published (bool): If True, publish immediately; if False, create as draft

    Returns:
        dict: Response JSON from dev.to API (includes article URL)
    """
    if not DEVTO_API_KEY:
        raise ValueError("DEVTO_API_KEY not found in .env file")

    payload = {
        "article": {
            "title": title,
            "body_markdown": body_markdown,
            "published": published
        }
    }

    if tags:
        payload["article"]["tags"] = tags

    response = requests.post(API_URL, json=payload, headers=HEADERS)

    if response.status_code not in (200, 201):
        print(f"Error: Failed to post to dev.to (status {response.status_code})")
        print(f"Response: {response.text}")
        return None

    return response.json()


if __name__ == "__main__":
    print("Posting test draft to dev.to...")
    result = post_to_devto(
        title="Test Post from Content Planner",
        body_markdown="This is a test draft.",
        tags=["test", "automation"],
        published=False
    )

    if result:
        print("Success! Article created as draft.")
        print(f"URL: {result.get('url')}")
        print(f"ID: {result.get('id')}")
    else:
        print("Failed to create article.")