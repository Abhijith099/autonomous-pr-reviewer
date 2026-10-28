import json
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from app.github.security import verify_github_signature

from app.agents.orchestrator import ReviewOrchestrator

orchestrator = ReviewOrchestrator()


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pr_reviewer")

app = FastAPI(
    title="Autonomous GitHub PR Reviewer",
    description="Deterministic multi-agent code review system powered by FastAPI and Groq",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "autonomous-pr-reviewer"}


async def process_pull_request_background(payload: dict):
  """Background task that runs the full multi-agent review."""
  pr_data = payload.get("pull_request", {})
  repo_data = payload.get("repository", {})

  pr_number = pr_data.get("number")
  repo_name = repo_data.get("full_name")

  if not repo_name or not pr_number:
    logger.error("Missing repository full_name or pr_number in webhook payload")
    return

  logger.info(
      f"Background worker starting review for {repo_name} PR #{pr_number}..."
  )
  # Execute the full multi-agent review pipeline!
  state = await orchestrator.execute_review(repo_name, pr_number)
  logger.info(
      f"Finished review for {repo_name} PR #{pr_number} with status:"
      f" {state.status}"
  )



@app.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_github_delivery: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    """Main GitHub webhook receiver."""
    # 1. Read raw body bytes for cryptographic verification
    raw_body = await request.body()

    # 2. Verify signature
    if not verify_github_signature(raw_body, x_hub_signature_256):
        logger.warning(f"Rejected unauthorized webhook delivery {x_github_delivery}")
        raise HTTPException(status_code=401, detail="Invalid HMAC-SHA256 signature")

    # 3. Parse JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 4. Handle ping event (GitHub sends this when you first add the webhook)
    if x_github_event == "ping":
        logger.info("Received GitHub ping event. Webhook is successfully connected!")
        return {"status": "pong", "delivery": x_github_delivery}

    # 5. Filter for pull_request events only
    if x_github_event != "pull_request":
        logger.info(f"Ignored non-PR event: {x_github_event}")
        return {"status": "ignored", "reason": f"Event {x_github_event} not handled"}

    action = payload.get("action")
    # Only review when a PR is opened, synchronized (new commit pushed), or reopened
    if action not in ["opened", "synchronize", "reopened"]:
        logger.info(f"Ignored PR action: {action}")
        return {"status": "ignored", "reason": f"Action {action} not reviewed"}

    # 6. Check for draft PRs
    is_draft = payload.get("pull_request", {}).get("draft", False)
    if is_draft:
        logger.info("Ignored draft PR.")
        return {"status": "ignored", "reason": "Draft PRs are not reviewed"}

    # 7. Queue review pipeline in the background so GitHub gets instant 200 OK
    background_tasks.add_task(process_pull_request_background, payload)

    return {
        "status": "queued",
        "delivery": x_github_delivery,
        "repo": payload.get("repository", {}).get("full_name"),
        "pr_number": payload.get("pull_request", {}).get("number"),
    }
