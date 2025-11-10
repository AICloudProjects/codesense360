from dotenv import load_dotenv
import os
import boto3
import requests

# Load environment variables from .env
load_dotenv()

print("🔹 GitHub Token Found:", bool(os.getenv("GITHUB_TOKEN")))
print("🔹 AWS Key Found:", bool(os.getenv("AWS_ACCESS_KEY_ID")))

# --- AWS Test ---
try:
    s3 = boto3.client("s3")
    s3.list_buckets()
    print("✅ AWS connection successful")
except Exception as e:
    print("⚠️ AWS error:", e)

# --- GitHub Test ---
try:
    headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}
    r = requests.get("https://api.github.com/user", headers=headers)
    if r.status_code == 200:
        print(f"✅ GitHub connected as: {r.json().get('login')}")
    else:
        print(f"⚠️ GitHub error: {r.status_code} {r.text}")
except Exception as e:
    print("⚠️ GitHub error:", e)
