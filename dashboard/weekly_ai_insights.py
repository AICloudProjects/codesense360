import os, json
import boto3
import pandas as pd
from datetime import datetime
from openai import OpenAI

# Initialize clients
athena = boto3.client("athena", region_name=os.getenv("AWS_REGION"))
s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ATHENA_DB = "codesense360_db"
S3_OUTPUT = "s3://codesense360-data/athena-results/"
S3_BUCKET = "codesense360-data"

def run_query(query):
    """Run Athena query and return DataFrame."""
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": S3_OUTPUT},
    )
    exec_id = response["QueryExecutionId"]

    # Wait for completion
    while True:
        res = athena.get_query_execution(QueryExecutionId=exec_id)
        state = res["QueryExecution"]["Status"]["State"]
        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break

    if state != "SUCCEEDED":
        raise Exception(f"Athena query failed: {state}")

    result = athena.get_query_results(QueryExecutionId=exec_id)
    cols = [col["Label"] for col in result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
    rows = [r["Data"] for r in result["ResultSet"]["Rows"][1:]]
    data = [[c.get("VarCharValue", "") for c in row] for row in rows]
    return pd.DataFrame(data, columns=cols)

def generate_summary():
    commits_df = run_query("""
        SELECT author_login, COUNT(*) AS commits
        FROM commits_processed
        WHERE author_login IS NOT NULL
        GROUP BY author_login
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

    prompt = f"""
    You are an engineering analytics assistant.
    Summarize weekly developer performance trends using:
    - Commits: {commits_df.to_dict(orient='records')}
    - Pull Requests: {pr_df.to_dict(orient='records')}
    - CI/CD runs: {cicd_df.to_dict(orient='records')}
    Use emojis 📈📉 and produce a short summary under 150 words.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.6,
    )

    insights = response.choices[0].message.content
    print("✅ Weekly AI Insights Generated:\n", insights)
    return insights

if __name__ == "__main__":
    insights = generate_summary()

    output_key = f"weekly_insights/insight_{datetime.utcnow().strftime('%Y%m%d')}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=json.dumps({"timestamp": datetime.utcnow().isoformat(), "insights": insights}, indent=2),
        ContentType="application/json"
    )
    print(f"📦 Saved to s3://{S3_BUCKET}/{output_key}")
