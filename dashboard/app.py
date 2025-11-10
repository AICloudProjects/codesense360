import streamlit as st
import boto3
import pandas as pd
import yaml
import os
from io import StringIO

# --- Page setup ---
st.set_page_config(page_title="CodeSense360 Dashboard", layout="wide")

# --- Load config ---
with open("dashboard/config.yaml", "r") as f:
    config = yaml.safe_load(f)

region = config["aws"]["region"]
athena_db = config["aws"]["athena_database"]
output_bucket = config["aws"]["bucket"]
output_location = config["aws"]["athena_output"]

# --- Boto3 clients (use Streamlit secrets for credentials) ---
athena = boto3.client(
    "athena",
    region_name=region,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
s3 = boto3.client(
    "s3",
    region_name=region,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# --- Utility: Run Athena query ---
def run_query(query):
    st.info(f"🔍 Running query:\n{query}")
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": athena_db},
        ResultConfiguration={"OutputLocation": output_location},
    )
    query_id = response["QueryExecutionId"]

    # Poll for completion
    state = "RUNNING"
    while state in ("RUNNING", "QUEUED"):
        res = athena.get_query_execution(QueryExecutionId=query_id)
        state = res["QueryExecution"]["Status"]["State"]

    if state != "SUCCEEDED":
        st.error(f"❌ Query failed: {state}")
        return pd.DataFrame()

    # Download CSV from S3
    key = f"athena-query-results/{query_id}.csv"
    data = s3.get_object(Bucket=output_bucket, Key=key)
    return pd.read_csv(StringIO(data["Body"].read().decode("utf-8")))

# --- Sidebar ---
st.sidebar.header("📊 Choose View")
view = st.sidebar.radio(
    "Select Metric",
    ["Commits", "Pull Requests", "Author PR Summary", "CI/CD Runs"]
)

# --- Views ---
if view == "Commits":
    st.title("🧩 Commit Trends")
    df = run_query("""
        SELECT author_login AS author, COUNT(*) AS commits
        FROM commits_processed
        WHERE author_login IS NOT NULL
        GROUP BY author
        ORDER BY commits DESC
        LIMIT 10;
    """)
    st.bar_chart(df.set_index("author"))

elif view == "Pull Requests":
    st.title("🔀 Pull Request Metrics")
    df = run_query("""
        SELECT author, COUNT(*) AS total_prs,
               SUM(CASE WHEN merged THEN 1 ELSE 0 END) AS merged_prs,
               ROUND(AVG(review_time_hours),2) AS avg_review_time
        FROM pull_requests_processed
        GROUP BY author
        ORDER BY merged_prs DESC
        LIMIT 10;
    """)
    st.dataframe(df)
    st.bar_chart(df.set_index("author")[["merged_prs"]])

elif view == "Author PR Summary":
    st.title("👥 Developer PR Summary")
    df = run_query("SELECT * FROM author_pr_summary ORDER BY merged_prs DESC LIMIT 15;")
    st.dataframe(df)

else:
    st.title("⚙️ CI/CD Workflow Health")
    df = run_query("""
        SELECT conclusion, COUNT(*) AS total
        FROM workflow_runs_processed
        GROUP BY conclusion;
    """)
    st.bar_chart(df.set_index("conclusion"))

st.success("✅ Dashboard ready")
