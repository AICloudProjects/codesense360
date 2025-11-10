import json
import logging
import traceback

# Configure logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Core imports from your project
try:
    from src.ingest.github_ingest import (
        fetch_commits,
        fetch_pull_requests,
        fetch_pr_details,
        save_to_local,
        upload_to_s3,
    )
    from src.process.metrics_processor import (
        process_commits,
        process_pull_requests,
        save_processed,
    )
except Exception as import_error:
    logger.error("❌ Module import failed: %s", import_error)
    raise


def lambda_handler(event, context):
    """Main Lambda entrypoint for CodeSense360 pipeline."""
    logger.info("🚀 CodeSense360 Lambda execution started")

    try:
        # Step 1: Fetch GitHub data
        commits = fetch_commits()
        prs = fetch_pull_requests()
        detailed_prs = fetch_pr_details(prs)
        logger.info("✅ Retrieved %d commits and %d PRs", len(commits), len(detailed_prs))

        # Step 2: Save locally (Lambda /tmp/ dir is writable)
        commit_file = save_to_local(commits, "commits.json")
        pr_file = save_to_local(detailed_prs, "pull_requests_detailed.json")

        # Step 3: Upload raw data to S3
        upload_to_s3(commit_file, s3_folder="github/")
        upload_to_s3(pr_file, s3_folder="github/")

        # Step 4: Process metrics
        commit_df, commit_metrics = process_commits(commits)
        pr_df, pr_metrics, author_metrics = process_pull_requests(detailed_prs)

        save_processed(commit_df, "commits_processed")
        save_processed(pr_df, "pull_requests_processed")
        save_processed(author_metrics, "author_pr_summary")

        logger.info("✅ CodeSense360 Lambda run complete")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "✅ CodeSense360 Lambda run complete",
                "commit_metrics": commit_metrics,
                "pr_metrics": pr_metrics
            }),
        }

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error("❌ Lambda execution failed: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "traceback": error_details
            }),
        }
