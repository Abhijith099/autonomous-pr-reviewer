import hashlib
import hmac
import json
import httpx
from app.config import settings
# 1. Dummy GitHub Pull Request payload
mock_payload = {
    "action": "opened",
    "number": 101,
    "pull_request": {
        "number": 101,
        "title": "feat: add user authentication",
        "draft": False,
        "user": {"login": "developer-abhijith"},
        "base": {"ref": "main"},
        "head": {"ref": "feature/auth", "sha": "abc123def456"},
    },
    "repository": {
        "id": 987654321,
        "name": "demo-repo",
        "full_name": "Abhijith099/demo-repo",
        "owner": {"login": "Abhijith099"},
        "default_branch": "main",
    },
}
raw_bytes = json.dumps(mock_payload).encode("utf-8")
# 2. Compute the exact HMAC signature GitHub would generate
secret = settings.GITHUB_WEBHOOK_SECRET
mac = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256)
signature = f"sha256={mac.hexdigest()}"
# 3. Send to our local FastAPI server
headers = {
    "Content-Type": "application/json",
    "X-GitHub-Event": "pull_request",
    "X-GitHub-Delivery": "delivery-uuid-9999",
    "X-Hub-Signature-256": signature,
}
print("Sending simulated GitHub webhook to http://127.0.0.1:8000/webhook...")
response = httpx.post(
    "http://127.0.0.1:8000/webhook", content=raw_bytes, headers=headers
)
print(f"\nResponse Code: {response.status_code}")
print(f"Response Body: {response.json()}")