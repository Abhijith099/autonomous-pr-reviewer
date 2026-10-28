import hashlib
import hmac
import json
import httpx
from app.config import settings

# 1. Simulate GitHub Webhook for PR #12000 on tiangolo/fastapi
mock_payload = {
    "action": "opened",
    "number": 12000,
    "pull_request": {
        "number": 12000,
        "title": "Add GitHub Action labeler",
        "draft": False,
        "user": {"login": "tiangolo"},
        "base": {"ref": "master"},
        "head": {"ref": "patch-1", "sha": "abc123"},
    },
    "repository": {
        "id": 160919119,
        "name": "fastapi",
        "full_name": "tiangolo/fastapi",
        "owner": {"login": "tiangolo"},
        "default_branch": "master",
    },
}

raw_bytes = json.dumps(mock_payload).encode("utf-8")

# 2. Compute the exact HMAC signature
secret = settings.GITHUB_WEBHOOK_SECRET
mac = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256)
signature = f"sha256={mac.hexdigest()}"

# 3. Send to our local FastAPI server
headers = {
    "Content-Type": "application/json",
    "X-GitHub-Event": "pull_request",
    "X-GitHub-Delivery": "delivery-e2e-test-1",
    "X-Hub-Signature-256": signature,
}

print("Sending simulated GitHub webhook to http://127.0.0.1:8000/webhook...")
response = httpx.post(
    "http://127.0.0.1:8000/webhook", content=raw_bytes, headers=headers
)

print(f"\nResponse Code: {response.status_code}")
print(f"Response Body: {response.json()}")
