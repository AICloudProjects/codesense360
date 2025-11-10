from github_ingest import fetch_commits, fetch_pull_requests

def test_ingestion():
    commits = fetch_commits(since_days=3)
    assert isinstance(commits, list)
    prs = fetch_pull_requests(state="open")
    assert isinstance(prs, list)
    print("✅ GitHub ingestion tests passed!")

if __name__ == "__main__":
    test_ingestion()