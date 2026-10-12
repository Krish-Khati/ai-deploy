import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Use openai/gpt-oss-120b (current free-tier-accessible production model on Groq)
# llama-3.3-70b-versatile requires Enterprise plan and will fail on free accounts
MODEL = "openai/gpt-oss-120b"

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


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
You are a developer writing a short, engaging blog post for dev.to about a recent GitHub commit.

Repository: {repo_name}
Commit message: {commit_message}
Commit date: {commit_date}

Write a casual, developer-to-developer blog post (150-250 words) that:
- Has a catchy title
- Explains what the commit/project is about in simple terms
- Shares why it matters or what's interesting
- Uses a friendly, conversational tone
- Includes a brief code snippet or technical detail if relevant

Respond in this EXACT format:
TITLE: Your Blog Post Title Here
BODY: Your markdown body here with proper formatting
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a developer blogger who writes engaging, concise posts for dev.to."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()

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

            # Post to dev.to as draft
            print("\nPosting to dev.to as draft...")
            try:
                result = post_to_devto(
                    title=post['title'],
                    body_markdown=post['body'],
                    tags=['github', 'ai', 'automation'],
                    published=False
                )
                if result:
                    print(f"Success! Draft created: {result.get('url')}")
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