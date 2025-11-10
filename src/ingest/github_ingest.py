import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
#from s3_uploader import upload_to_s3
from src.ingest.s3_uploader import upload_to_s3


load_dotenv()

# Load credentials
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
REPO_NAME = os.getenv("GITHUB_REPO_NAME")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

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

def fetch_pull_requests(state="all", per_page=100, max_pages=50, sort="created", direction="desc"):
    """
    Fetch pull requests with pagination.
    Returns a list of PRs across up to max_pages pages.
    """
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    prs = []
    page = 1
    while page <= max_pages:
        params = {
            "state": state,          # open | closed | all
            "per_page": per_page,    # up to 100
            "page": page,
            "sort": sort,            # created | updated | popularity | long-running
            "direction": direction   # desc | asc
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
    """
    Enrich each PR with detailed metadata:
    merged_at, merged_by, review_comments, commits, additions/deletions, etc.
    """
    detailed_prs = []
    for pr in prs:
        pr_number = pr["number"]
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            pr_detail = r.json()
            # Merge top-level + detailed fields
            merged = {**pr, **{
                "merged_at": pr_detail.get("merged_at"),
                "merged_by": pr_detail.get("merged_by", {}).get("login"),
                "additions": pr_detail.get("additions"),
                "deletions": pr_detail.get("deletions"),
                "changed_files": pr_detail.get("changed_files"),
                "review_comments": pr_detail.get("review_comments"),
                "commits_in_pr": pr_detail.get("commits"),
            }}
            detailed_prs.append(merged)
        else:
            print(f"⚠️ Could not fetch PR #{pr_number}: {r.status_code}")
    print(f"✅ Enriched {len(detailed_prs)} PRs with detailed metadata")
    return detailed_prs


def save_to_local(data, filename):
    """Save data locally as JSON (for now)."""
    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", filename)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(data)} records to {file_path}")
    return file_path

if __name__ == "__main__":
    commits = fetch_commits()
    prs = fetch_pull_requests()
    detailed_prs = fetch_pr_details(prs)

    #save locally
    commit_file = save_to_local(commits, "commits.json")
    #pr_file = save_to_local(prs, "pull_requests.json")
    detailed_pr_file = save_to_local(detailed_prs, "pull_requests_detailed.json")
    # --- New: push to S3 ---
    upload_to_s3(commit_file, s3_folder="github/")
    #upload_to_s3(pr_file, s3_folder="github/")
    upload_to_s3(detailed_pr_file, s3_folder="github/")
