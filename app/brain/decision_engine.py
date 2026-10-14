import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Use openai/gpt-oss-120b (current free-tier-accessible production model on Groq)
# llama-3.3-70b-versatile requires Enterprise plan and will fail on free accounts
MODEL = "openai/gpt-oss-120b"

# Network calls to Groq fail intermittently on this machine, so retry a few times.
MAX_ATTEMPTS = 3

# The SDK's default connect timeout is only 5s, which intermittently trips on a
# slow connection and surfaces as an unhelpful generic "Connection error".
client = Groq(api_key=GROQ_API_KEY, timeout=120.0) if GROQ_API_KEY else None


# A blog title is a sentence about an idea or a feeling, not a description of a
# photo. Handing its literal words to a stock image index reliably returns
# nothing: searching "missing env variable documentation" matches no photo in
# existence, because no one photographs "missing". So map the title onto the
# visual theme it implies and search for that instead.
#
# Ordered most-specific to most-generic. Ties keep the earlier theme.
IMAGE_THEMES = [
    ("artificial intelligence technology",
     ["ai", "llm", "gpt", "neural", "prompt", "chatbot", "machine learning",
      "language model", "inference", "embedding"]),
    ("programmer debugging code screen",
     ["bug", "debug", "debugging", "error", "crash", "crashed", "broken",
      "exception", "stack trace", "regression", "failure", "failed"]),
    ("software configuration code",
     ["env", "dotenv", "environment variable", "config", "configuration",
      "secret", "api key", "credential", "missing", "undocumented",
      "not documented", "typo"]),
    ("server rack data center",
     ["deploy", "deployment", "docker", "kubernetes", "infrastructure",
      "server", "production", "pipeline", "downtime", "outage"]),
    ("terminal command line screen",
     ["terminal", "shell", "cli", "command line", "bash", "script", "cron",
      "linux", "ssh"]),
    ("source code on computer screen",
     ["git", "commit", "branch", "merge", "rebase", "pull request", "repo",
      "repository", "diff", "version control"]),
    ("cyber security lock code",
     ["security", "auth", "authentication", "oauth", "encrypt", "password",
      "token", "breach", "privacy", "hack"]),
    ("data dashboard charts",
     ["data", "analytics", "metric", "dashboard", "chart", "database", "sql",
      "query"]),
    ("software testing code review",
     ["test", "tests", "testing", "coverage", "tdd", "mock", "fixture",
      "code review", "review"]),
    ("developers collaborating at desk",
     ["team", "collaborate", "pair", "mentor", "cofounder", "client",
      "stakeholder", "feedback", "hire", "junior"]),
    ("tired developer at laptop desk",
     ["burnout", "tired", "exhausted", "motivation", "focus",
      "quit", "imposter", "procrastinat", "balance", "lonely",
      "weekend", "morning", "overtime"]),
    ("software developer coding laptop",
     ["developer", "coding", "code", "programming", "software", "build",
      "project", "tool", "learning", "beginner", "learn"]),
]

# Used when the title matches no theme at all.
DEFAULT_IMAGE_QUERY = "software developer coding"


def derive_image_query(title):
    """
    Turn a blog post title into a short image search query.

    Scores every visual theme by how many of its keywords appear in the title
    and returns the search phrase for the strongest match, falling back to a
    generic dev query when nothing matches.
    """
    if not title:
        return DEFAULT_IMAGE_QUERY

    text = title.lower()
    best_query, best_score = DEFAULT_IMAGE_QUERY, 0

    for query, keywords in IMAGE_THEMES:
        # Word boundaries matter: without them "ai" matches "maintain" and
        # "key" matches "monkey", which silently hijacks the theme choice.
        score = sum(
            1 for keyword in keywords
            if re.search(rf"\b{re.escape(keyword)}\b", text)
        )
        if score > best_score:
            best_query, best_score = query, score

    return best_query


def _console_safe(text, limit=500):
    """
    Make model output printable on the default Windows console.

    Windows consoles default to cp1252, so printing raw model text containing a
    non-breaking hyphen or an emoji raises UnicodeEncodeError. That exception
    used to be swallowed by the caller's broad except, hiding the real error.
    """
    return text[:limit].encode("ascii", "replace").decode()


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

Real, checkable context:
- Repo: {repo_name}
- Latest commit: {commit_message}
- Commit date: {commit_date}

Voice and perspective:
- Write as Krish, an indie developer based in India who builds software and AI tools and writes publicly about the process.
- Strictly first person. Use "I". This is honest reflection, not a tutorial.
- The commit is a starting point, not the subject. Write about what it prompted you to think about.

TRUTHFULNESS - this matters more than style:
- Do NOT invent incidents. No fabricated late nights, specific times, scenes, arguments, dialogue, people, or "I remember when..." stories.
- Do NOT claim a specific bug, outage, or client interaction unless it is stated in the commit message above.
- Write general, honest reflection about software development, AI tools, and content creation - the kind of thing a working developer would genuinely think. Real perspective, not a dramatised narrative.
- Referring to the commit plainly is fine and encouraged, e.g. "I made a small fix to the setup docs today." That part is actually true. Keep it boring and accurate.
- If you want to describe a struggle, describe it as a general pattern you deal with, not a specific story you are making up.
- When in doubt, write something dull and true rather than something vivid and invented.

Hard requirements:
- 200-300 words.
- Start with the thought itself, not with scene-setting. No throat-clearing.
- Take at least one firm, defensible position. Honest opinion is good; forced drama is not.
- Natural prose with varied sentence length. Contractions are good.
- NO emojis.
- Banned phrases: "Hey fellow devs", "In today's fast-paced world", "Let's dive in", "Conclusion", "In conclusion", "game-changer", "leverage", "seamless", "robust", "delve", "tapestry", "unlock", "harness", "elevate", "deep dive", "buckle up".
- No bullet-point summaries, no numbered takeaways, no closing call-to-action, no hashtags, no em-dash-heavy cadence.

Finish on a plain, specific sentence. Not a question to the reader.

Respond in EXACTLY this format and nothing else:
TITLE: <single line title, no quotes, no markdown>
BODY: <the markdown body>
"""

    # Transient TLS/connection faults (measured ~40% failure rate on this
    # machine's network) are worth retrying; bad prompts are not.
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are an indie developer who writes honest, personal engineering journal posts. You never use emojis or marketing filler. You never invent events, conversations, scenes, or specific incidents that did not happen."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                # This is a reasoning model: it spends tokens thinking before
                # writing, billed against the same budget as the post itself.
                # Reasoning runs 1400-1600 tokens on this prompt, so leave
                # generous headroom or the response gets truncated before any
                # content is produced.
                max_tokens=8000,
                # Keep the chain-of-thought out of the text we parse for TITLE/BODY
                reasoning_format="parsed"
            )
            break
        except Exception as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                print(f"  Groq request failed ({type(e).__name__}), retrying {attempt}/{MAX_ATTEMPTS - 1}...")
    else:
        print(f"Error calling Groq API after {MAX_ATTEMPTS} attempts: {last_error}")
        return None

    try:
        content = (response.choices[0].message.content or "").strip()

        # If the model ran out of room, tell the user instead of failing silently
        if response.choices[0].finish_reason == "length":
            print("Error: response was cut off (finish_reason='length')")
            print(f"Raw response: '{_console_safe(content)}'")
            return None

        # Parse title and body
        if "TITLE:" in content and "BODY:" in content:
            title_part = content.split("TITLE:")[1].split("BODY:")[0].strip()
            body_part = content.split("BODY:")[1].strip()
            return {"title": title_part, "body": body_part}
        else:
            print("Error: Unexpected response format from LLM")
            print(f"Raw response: '{_console_safe(content)}'")
            return None

    except Exception as e:
        print(f"Error processing LLM response: {e}")
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
                    derived_query = derive_image_query(title)
                    fallback_queries = [
                        "software developer coding",
                        "programming laptop",
                        "developer workspace",
                    ]
                    print(f"  Title: '{title}'")
                    print(f"  Derived query: '{derived_query}'")
                    print(f"  Fallback queries: {fallback_queries}")
                    cover_image = get_relevant_image(
                        derived_query,
                        fallback_queries=fallback_queries,
                    )
                except Exception as e:
                    print(f"  Cover image lookup failed (posting without one): {e}")

                if cover_image:
                    print(f"  Cover image: {cover_image}")
                else:
                    print("  No cover image found - posting without one.")

                # Create as a draft so a human reviews it before it goes live
                print("\nCreating draft on dev.to (manual review required)...")
                try:
                    result = post_to_devto(
                        title=title,
                        body_markdown=body,
                        tags=['github', 'ai', 'automation'],
                        published=False,
                        main_image=cover_image
                    )
                    if result:
                        print(f"Draft created: {result.get('url')}")
                        print("Review it on dev.to, then publish when ready.")
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