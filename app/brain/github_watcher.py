import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"


def get_latest_activity(repo="krish-khati/ai-deploy"):
    """
    Fetch latest commits and release from a GitHub repository.

    Args:
        repo (str): Repository in format "owner/repo"

    Returns:
        dict: Contains latest_commit_message, latest_commit_date,
              latest_release_tag, latest_release_name
    """
    result = {
        "latest_commit_message": None,
        "latest_commit_date": None,
        "latest_release_tag": None,
        "latest_release_name": None
    }

    # Get latest commits
    commits_url = f"{BASE_URL}/repos/{repo}/commits"
    commits_response = requests.get(commits_url, headers=HEADERS)

    if commits_response.status_code == 200:
        commits = commits_response.json()
        if commits:
            latest_commit = commits[0]
            result["latest_commit_message"] = latest_commit["commit"]["message"]
            result["latest_commit_date"] = latest_commit["commit"]["author"]["date"]
    else:
        print(f"Error fetching commits: {commits_response.status_code} - {commits_response.text}")

    # Get latest release (404 is OK if no releases exist)
    releases_url = f"{BASE_URL}/repos/{repo}/releases/latest"
    releases_response = requests.get(releases_url, headers=HEADERS)

    if releases_response.status_code == 200:
        release = releases_response.json()
        result["latest_release_tag"] = release.get("tag_name")
        result["latest_release_name"] = release.get("name")
    elif releases_response.status_code == 404:
        # No releases yet - this is expected for new repos
        pass
    else:
        print(f"Error fetching releases: {releases_response.status_code} - {releases_response.text}")

    return result


if __name__ == "__main__":
    print("Fetching latest GitHub activity...")
    activity = get_latest_activity()

    print("\n--- Latest Activity ---")
    print(f"Latest Commit: {activity['latest_commit_message']}")
    print(f"Commit Date:   {activity['latest_commit_date']}")
    print(f"Latest Release Tag:  {activity['latest_release_tag'] or 'None'}")
    print(f"Latest Release Name: {activity['latest_release_name'] or 'None'}")