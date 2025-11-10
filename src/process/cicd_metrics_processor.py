import json, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.ingest.s3_uploader import upload_to_s3

load_dotenv()
DATA_DIR = "/tmp/data"  # ✅ Writable directory in Lambda

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        data = json.load(f)
    print(f"📂 Loaded {len(data)} workflow runs")
    return data

def process_workflow_runs(runs):
    df = pd.json_normalize(runs)
    if df.empty:
        print("⚠️ No workflow data.")
        return df, {}

    df["created_at"] = pd.to_datetime(df["created_at"])
    df["updated_at"] = pd.to_datetime(df["updated_at"])
    df["run_time_min"] = (df["updated_at"] - df["created_at"]).dt.total_seconds() / 60

    metrics = {
        "total_runs": len(df),
        "success_rate_%": round((df["conclusion"].eq("success").mean()) * 100, 2),
        "avg_runtime_min": round(df["run_time_min"].mean(), 2),
        "failed_runs": int(df["conclusion"].ne("success").sum()),
        "latest_run": df["created_at"].max(),
    }

    print("🧮 CI/CD Metrics:", metrics)
    return df, metrics

def save_processed(df, name):
    if df.empty:
        print("ℹ️ Skipping empty CI/CD dataset.")
        return
    processed_dir = os.path.join(DATA_DIR, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    file_path = os.path.join(processed_dir, f"{name}.csv")
    df.to_csv(file_path, index=False)
    print(f"💾 Saved → {file_path}")
    upload_to_s3(file_path, s3_folder="processed/")
    
    # ✅ Optional cleanup to save /tmp space
    try:
        os.remove(file_path)
        print(f"🧹 Cleaned up temp file {file_path}")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

    return file_path

if __name__ == "__main__":
    runs = load_json("workflow_runs.json")
    df, metrics = process_workflow_runs(runs)
    save_processed(df, "workflow_runs_processed")
