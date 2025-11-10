import os
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = "codesense360-data"   # or read from config if you prefer

# Create an S3 client
s3 = boto3.client("s3", region_name=AWS_REGION)

def upload_to_s3(file_path, s3_folder="raw/"):
    """Upload a local file to S3 in the given folder."""
    file_name = os.path.basename(file_path)
    s3_key = f"{s3_folder}{file_name}"

    try:
        s3.upload_file(file_path, BUCKET_NAME, s3_key)
        print(f"✅ Uploaded {file_name} → s3://{BUCKET_NAME}/{s3_key}")
        return True
    except Exception as e:
        print(f"⚠️ Upload failed for {file_name}: {e}")
        return False

if __name__ == "__main__":
    # quick local test
    upload_to_s3("data/commits.json")