import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from src.ingest.s3_uploader import upload_to_s3

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER   = os.getenv("GITHUB_REPO_OWNER")
REPO_NAME    = os.getenv("GITHUB_REPO_NAME")
HEADERS      = {"Authorization": f"token {GITHUB_TOKEN}"}

DATA_DIR = "/tmp/data"  # ✅ writable in AWS Lambda

def fetch_workflow_runs(status="completed", per_page=50, max_pages=5):
    """Fetch recent workflow runs (builds) from GitHub Actions."""
    all_runs = []
    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
        params = {"status": status, "per_page": per_page, "page": page}
        r = requests.get(url, headers=HEADERS, params=params)
        if r.status_code != 200:
            print(f"⚠️ Error {r.status_code} on page {page}")
            break
        runs = r.json().get("workflow_runs", [])
        if not runs:
            break
        all_runs.extend(runs)
    print(f"✅ Retrieved {len(all_runs)} workflow runs")
    return all_runs

def save_to_local(data, filename):
    """Save workflow run data locally in /tmp before uploading to S3."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, filename)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(data)} records → {file_path}")
    return file_path


if __name__ == "__main__":
    runs = fetch_workflow_runs()
    runs_file = save_to_local(runs, "workflow_runs.json")
    upload_to_s3(runs_file, s3_folder="cicd/")
