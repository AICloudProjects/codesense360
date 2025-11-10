import json
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.ingest.s3_uploader import upload_to_s3

load_dotenv()

DATA_DIR = "/tmp/data"  # ✅ Writable directory in Lambda

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        data = json.load(f)
    print(f"📂 Loaded {len(data)} records from {filename}")
    return data

def process_commits(commits):
    df = pd.json_normalize(commits)
    df["author"] = df["commit.author.name"]
    df["date"] = pd.to_datetime(df["commit.author.date"])
    df["message_len"] = df["commit.message"].str.len()

    metrics = {
        "total_commits": len(df),
        "unique_authors": df["author"].nunique(),
        "avg_message_length": df["message_len"].mean(),
        "first_commit": df["date"].min(),
        "last_commit": df["date"].max(),
    }
    print("🧮 Commit metrics:", metrics)
    return df, metrics


def process_pull_requests(prs):
    df = pd.json_normalize(prs)
    if df.empty:
        print("⚠️ No PR data found.")
        return df, {"total_prs": 0}, pd.DataFrame()

    df["created_at"] = pd.to_datetime(df["created_at"])
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    df["merged_at"] = pd.to_datetime(df.get("merged_at"))
    df["author"] = df["user.login"]
    df["merged"] = df["merged_at"].notnull()
    df["review_time_hours"] = (df["closed_at"] - df["created_at"]).dt.total_seconds() / 3600

    author_metrics = (
        df.groupby("author")
        .agg(
            total_prs=("number", "count"),
            merged_prs=("merged", "sum"),
            avg_review_time_hours=("review_time_hours", "mean"),
            avg_comments=("review_comments", "mean"),
        )
        .reset_index()
    )

    overall_metrics = {
        "total_prs": len(df),
        "merged_prs": int(df["merged"].sum()),
        "avg_review_time_hours": round(df["review_time_hours"].mean(), 2),
        "merge_ratio": round(df["merged"].mean() * 100, 1),
    }

    print("🧮 Overall PR metrics:", overall_metrics)
    print("👥 Per-author metrics:\n", author_metrics)
    return df, overall_metrics, author_metrics


def save_processed(df, name):
    if df is None or df.empty:
        print(f"ℹ️ Skipping save: {name} is empty")
        return None

    processed_dir = os.path.join(DATA_DIR, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    file_path = os.path.join(processed_dir, f"{name}.csv")
    df.to_csv(file_path, index=False)
    print(f"💾 Saved processed data → {file_path}")
    upload_to_s3(file_path, s3_folder="processed/")

    # ✅ Optional cleanup to free /tmp space
    try:
        os.remove(file_path)
        print(f"🧹 Cleaned up temp file {file_path}")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

    return file_path


if __name__ == "__main__":
    commits = load_json("commits.json")
    prs = load_json("pull_requests_detailed.json")

    commit_df, commit_metrics = process_commits(commits)
    pr_df, pr_metrics, author_metrics = process_pull_requests(prs)

    save_processed(commit_df, "commits_processed")
    save_processed(pr_df, "pull_requests_processed")
    save_processed(author_metrics, "author_pr_summary")

    print("\n✅ Processing complete.")
