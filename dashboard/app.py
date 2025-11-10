import streamlit as st
import boto3
import pandas as pd
import yaml
import os
from io import StringIO


st.sidebar.write("🔑 AWS Key Found:", bool(os.getenv("AWS_ACCESS_KEY_ID")))
st.sidebar.write("🌎 AWS Region:", os.getenv("AWS_REGION"))

try:
    sts = boto3.client("sts")
    whoami = sts.get_caller_identity()
    st.sidebar.success(f"✅ Connected as {whoami['Arn']}")
except Exception as e:
    st.sidebar.error(f"❌ AWS Connection failed: {e}")


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

import openai
from datetime import datetime, timedelta

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_ai_insights():
    """Auto-generate and persist AI-driven insights."""
    st.subheader("🤖 AI Insights")

    # Load current metrics from Athena
    commits_df = run_query("""
        SELECT author_login AS author, COUNT(*) AS commits
        FROM commits_processed
        WHERE author_login IS NOT NULL
        GROUP BY author
        ORDER BY commits DESC
        LIMIT 10;
    """)

    pr_df = run_query("""
        SELECT author, total_prs, merged_prs, avg_review_time_hours
        FROM author_pr_summary
        ORDER BY merged_prs DESC
        LIMIT 10;
    """)

    cicd_df = run_query("""
        SELECT conclusion, COUNT(*) AS total
        FROM workflow_runs_processed
        GROUP BY conclusion;
    """)

    # Use previous summary if available
    insights_cache = "dashboard/insights_cache.json"
    cached = None
    if os.path.exists(insights_cache):
        with open(insights_cache, "r") as f:
            cached = json.load(f)
            st.info(f"🕒 Last generated: {cached['generated_at']}")
            st.markdown(cached["insights"])

    # Offer refresh option
    if st.button("🔄 Refresh AI Insights"):
        prompt = f"""
        You are an analytics assistant for a DevOps productivity dashboard.

        Using this week's GitHub and CI/CD data:
        - Commits by author: {commits_df.to_dict(orient='records')}
        - Pull Request Summary: {pr_df.to_dict(orient='records')}
        - CI/CD Build Results: {cicd_df.to_dict(orient='records')}

        Compare these results with last week (if provided below), identify trends,
        and produce a concise executive summary (<200 words) highlighting:
        1️⃣ Developer performance trends
        2️⃣ PR efficiency or delays
        3️⃣ Build reliability
        4️⃣ Key improvements or risks

        Previous insights for context:
        {cached["insights"] if cached else "No previous summary."}

        Use emojis like 📈 for improvements and 📉 for regressions.
        """

        with st.spinner("🧠 Generating AI summary..."):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=400
                )
                insights = response["choices"][0]["message"]["content"]

                # Display and cache
                st.success("✅ Insights updated")
                st.markdown(insights)
                with open(insights_cache, "w") as f:
                    json.dump({
                        "generated_at": datetime.utcnow().isoformat(),
                        "insights": insights
                    }, f, indent=2)
            except Exception as e:
                st.error(f"⚠️ OpenAI request failed: {e}")

# Sidebar persistent section
st.sidebar.divider()
st.sidebar.markdown("### 🤖 AI Insights")
generate_ai_insights()
