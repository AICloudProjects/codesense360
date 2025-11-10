import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.ingest.s3_uploader import upload_to_s3

# Load environment variables from .env only if running locally
if os.getenv("AWS_LAMBDA_FUNCTION_NAME") is None:
    load_dotenv()

# --- Load credentials ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# Defensive check to avoid None/None repo paths
if not all([GITHUB_TOKEN, REPO_OWNER, REPO_NAME]):
    raise EnvironmentError("❌ Missing required GitHub environment variables.")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}


# --- GitHub API functions ---
def fetch_commits(since_days=7, per_page=50):
    """Fetch recent commits from the GitHub repo."""
    since_date = (datetime.utcnow() - timedelta(days=since_days)).isoformat() + "Z"
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    params = {"since": since_date, "per_page": per_page}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    commits = r.json()
    print(f"✅ Retrieved {len(commits)} commits since {since_date}")
    return commits


def fetch_pull_requests(state="all", per_page=100, max_pages=20, sort="created", direction="desc"):
    """Fetch pull requests with pagination."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    prs = []
    page = 1
    while page <= max_pages:
        params = {
            "state": state,
            "per_page": per_page,
            "page": page,
            "sort": sort,
            "direction": direction,
        }
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        prs.extend(batch)
        page += 1
    print(f"✅ Retrieved {len(prs)} pull requests ({state}, paginated)")
    return prs


def fetch_pr_details(prs):
    """Enrich each PR with metadata like merge info, changes, etc."""
    detailed_prs = []
    for pr in prs:
        pr_number = pr.get("number")
        if not pr_number:
            continue
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            pr_detail = r.json()
            merged = {
                **pr,
                "merged_at": pr_detail.get("merged_at"),
                "merged_by": pr_detail.get("merged_by", {}).get("login"),
                "additions": pr_detail.get("additions"),
                "deletions": pr_detail.get("deletions"),
                "changed_files": pr_detail.get("changed_files"),
                "review_comments": pr_detail.get("review_comments"),
                "commits_in_pr": pr_detail.get("commits"),
            }
            detailed_prs.append(merged)
        else:
            print(f"⚠️ Could not fetch PR #{pr_number}: {r.status_code}")
    print(f"✅ Enriched {len(detailed_prs)} PRs with detailed metadata")
    return detailed_prs


# --- Lambda-safe save + upload ---
def save_to_local(data, filename):
    """Save data to /tmp, then upload to S3."""
    temp_dir = "/tmp/data"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"💾 Saved {len(data)} records → {file_path}")
    return file_path


# --- Main runner (for local testing only) ---
if __name__ == "__main__":
    print("🚀 Running GitHub ingest locally...")

    commits = fetch_commits()
    prs = fetch_pull_requests()
    detailed_prs = fetch_pr_details(prs)

    commit_file = save_to_local(commits, "commits.json")
    detailed_pr_file = save_to_local(detailed_prs, "pull_requests_detailed.json")

    upload_to_s3(commit_file, s3_folder="github/")
    upload_to_s3(detailed_pr_file, s3_folder="github/")

    print("✅ Local run complete.")
