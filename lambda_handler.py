import json
import logging
import sys
import traceback

# Configure logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# --- Diagnostic check block ---
def check_numpy_pandas():
    """Check if NumPy and Pandas are available in the runtime."""
    result = {}
    try:
        import numpy as np
        import pandas as pd
        result["numpy_version"] = np.__version__
        result["pandas_version"] = pd.__version__
        result["numpy_path"] = np.__file__
        result["pandas_path"] = pd.__file__
    except Exception as e:
        result["error"] = f"Dependency import failed: {str(e)}"
        logger.warning("⚠️ Diagnostic error: %s", e)
    result["sys_path"] = sys.path
    return result
# --- End diagnostic block ---


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
    """Main Lambda entrypoint."""
    logger.info("🚀 CodeSense360 Lambda execution started")
    diagnostics = check_numpy_pandas()

    try:
        # Step 1: Fetch GitHub data
        commits = fetch_commits()
        prs = fetch_pull_requests()
        detailed_prs = fetch_pr_details(prs)
        logger.info("✅ Retrieved %d commits and %d PRs", len(commits), len(detailed_prs))

        # Step 2: Save locally (Lambda /tmp/)
        commit_file = save_to_local(commits, "commits.json")
        pr_file = save_to_local(detailed_prs, "pull_requests_detailed.json")

        # Step 3: Upload to S3
        upload_to_s3(commit_file, s3_folder="github/")
        upload_to_s3(pr_file, s3_folder="github/")

        diagnostics["message"] = "✅ CodeSense360 Lambda run complete"
        result = {"statusCode": 200, "body": json.dumps(diagnostics)}

        logger.info("✅ Lambda completed successfully")
        return result

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error("❌ Lambda execution failed: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "traceback": error_details
            })
        }