import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Use openai/gpt-oss-120b (current free-tier-accessible production model on Groq)
# llama-3.3-70b-versatile requires Enterprise plan and will fail on free accounts
MODEL = "openai/gpt-oss-120b"

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def derive_image_query(title, max_words=5):
    """
    Turn a blog post title into a short image search query.

    Strips markdown/punctuation and keeps only the first few meaningful
    words, since image search engines do better with short queries.
    """
    if not title:
        return ""

    # Remove markdown emphasis/links and any non-alphanumeric characters
    cleaned = title.replace("#", " ").replace("*", " ").replace("`", " ")
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in cleaned)

    # Drop common filler words that make for poor image searches
    stop_words = {"the", "a", "an", "my", "our", "is", "to", "of", "and", "in",
                  "on", "for", "how", "why", "what", "i", "it", "with", "at"}

    words = [w for w in cleaned.lower().split() if w and w not in stop_words]
    return " ".join(words[:max_words])


def generate_blog_post(commit_message, commit_date, repo_name):
    """
    Generate a dev.to blog post from a GitHub commit using Groq LLM.

    Args:
        commit_message (str): The commit message
        commit_date (str): The commit date (ISO format)
        repo_name (str): Repository name (owner/repo)

    Returns:
        dict: {"title": str, "body": str} or None if error
    """
    if not client:
        print("Error: GROQ_API_KEY not found in .env file")
        return None

    prompt = f"""
Write a short personal blog post for dev.to (200-300 words).

Loose inspiration only (do NOT write a changelog, release note, or commit summary):
- Repo: {repo_name}
- Latest commit: {commit_message}
- Commit date: {commit_date}

Voice and perspective:
- Write as Krish, an indie developer based in India who builds software and AI tools and writes publicly about the process.
- Strictly first person. Use "I". This is a real journal entry from a working life, not a tutorial.
- The commit is just a spark. Write about what it made you think, notice, get stuck on, or reconsider.

Hard requirements:
- 200-300 words.
- Open with a concrete, specific moment: a late night, a bug, a conversation, a dead end. No throat-clearing.
- Include at least one firm opinion you hold, or one thing you got wrong and learned from. Generic positivity is not allowed.
- Natural prose with varied sentence length. Contractions are good.
- NO emojis.
- Banned phrases: "Hey fellow devs", "In today's fast-paced world", "Let's dive in", "Conclusion", "In conclusion", "game-changer", "leverage", "seamless", "robust", "delve", "tapestry", "unlock", "harness", "elevate", "deep dive", "buckle up".
- No bullet-point summaries, no numbered takeaways, no closing call-to-action, no hashtags, no em-dash-heavy cadence.

Finish on a plain, specific sentence. Not a question to the reader.

Respond in EXACTLY this format and nothing else:
TITLE: <single line title, no quotes, no markdown>
BODY: <the markdown body>
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an indie developer who writes honest, personal engineering journal posts. You never use emojis or marketing filler."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            # This is a reasoning model: it spends tokens thinking before writing.
            # Keep this limit comfortably above the 200-300 word target or the
            # response gets truncated before any content is produced.
            max_tokens=2000,
            # Keep the chain-of-thought out of the text we parse for TITLE/BODY
            reasoning_format="parsed"
        )

        content = (response.choices[0].message.content or "").strip()

        # If the model ran out of room, tell the user instead of failing silently
        if response.choices[0].finish_reason == "length":
            print("Error: response was cut off (finish_reason='length')")
            print(f"Raw response: '{content}'")
            return None

        # Parse title and body
        if "TITLE:" in content and "BODY:" in content:
            title_part = content.split("TITLE:")[1].split("BODY:")[0].strip()
            body_part = content.split("BODY:")[1].strip()
            return {"title": title_part, "body": body_part}
        else:
            print("Error: Unexpected response format from LLM")
            print(f"Raw response: '{content}'")
            return None

    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return None


if __name__ == "__main__":
    # Import get_latest_activity from github_watcher
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.brain.github_watcher import get_latest_activity
    from app.connectors.devto_connector import post_to_devto
    from app.generator.image_fetcher import get_relevant_image

    print("Fetching GitHub activity...")
    activity = get_latest_activity("Krish-Khati/ai-deploy")

    if activity["latest_commit_message"]:
        print(f"Found commit: {activity['latest_commit_message'][:60]}...")
        print("Generating blog post...\n")

        post = generate_blog_post(
            commit_message=activity["latest_commit_message"],
            commit_date=activity["latest_commit_date"],
            repo_name="Krish-Khati/ai-deploy"
        )

        if post:
            print("=" * 60)
            print(f"TITLE: {post['title'].encode('ascii', 'replace').decode()}")
            print("=" * 60)
            print(post["body"].encode('ascii', 'replace').decode())
            print("=" * 60)

            # Safety check: only publish if the AI output is substantial enough.
            # A short/empty title or body usually means the LLM returned broken output.
            MIN_BODY_LENGTH = 50
            title = (post['title'] or "").strip()
            body = (post['body'] or "").strip()

            if not title or len(body) < MIN_BODY_LENGTH:
                print("\nSkipping dev.to post: content didn't meet the minimum quality bar")
                print(f"  - Title must be non-empty (got {len(title)} chars)")
                print(f"  - Body must be at least {MIN_BODY_LENGTH} chars (got {len(body)})")
            else:
                # Find a relevant cover image (optional - skip quietly if none found)
                print("\nSearching for a cover image...")
                cover_image = None
                try:
                    # Titles are often metaphorical and search badly, so we keep
                    # a few generic dev-themed fallbacks behind the derived query.
                    cover_image = get_relevant_image(
                        derive_image_query(title),
                        fallback_queries=[
                            "software developer coding",
                            "programming laptop",
                            "developer workspace",
                        ],
                    )
                except Exception as e:
                    print(f"  Cover image lookup failed (posting without one): {e}")

                if cover_image:
                    print(f"  Cover image: {cover_image}")
                else:
                    print("  No cover image found - posting without one.")

                # Post to dev.to and publish immediately
                print("\nPosting to dev.to (publishing immediately)...")
                try:
                    result = post_to_devto(
                        title=title,
                        body_markdown=body,
                        tags=['github', 'ai', 'automation'],
                        published=True,
                        main_image=cover_image
                    )
                    if result:
                        print(f"Success! Published: {result.get('url')}")
                    else:
                        print("Failed to post to dev.to (check DEVTO_API_KEY)")
                except Exception as e:
                    print(f"Error posting to dev.to: {e}")
                    print("(Blog post content shown above)")
        else:
            print("Failed to generate blog post.")
    else:
        print("No commit found for this repository.")
        print("Try a different repo or check if the repo exists.")