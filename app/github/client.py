import logging
import httpx
from app.config import settings
from app.schemas import ChangedFile, PRContext

logger = logging.getLogger("pr_reviewer.github")

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Asynchronous HTTP client for interacting with the GitHub REST API."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _infer_language(self, filename: str) -> str:
        """Helper to guess the programming language from file extension."""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        mapping = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "jsx": "javascript",
            "sql": "sql",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "json": "json",
            "yaml": "yaml",
            "yml": "yaml",
            "md": "markdown",
            "sh": "shell",
        }
        return mapping.get(ext, "text")

    async def get_pr_context(self, repo_full_name: str, pr_number: int) -> PRContext:
        """Fetches PR metadata and all changed file diffs from GitHub."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0,follow_redirects=True) as client:
            # 1. Fetch Pull Request metadata
            pr_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}"
            logger.info(f"Fetching PR metadata from {pr_url}")
            pr_res = await client.get(pr_url)
            pr_res.raise_for_status()
            pr_data = pr_res.json()

            # 2. Fetch changed files and diffs
            files_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/files"
            logger.info(f"Fetching changed files from {files_url}")
            files_res = await client.get(files_url)
            files_res.raise_for_status()
            files_data = files_res.json()

            # 3. Parse changed files into our Pydantic schema
            changed_files: list[ChangedFile] = []
            for f in files_data:
                filename = f.get("filename", "")
                changed_files.append(
                    ChangedFile(
                        filename=filename,
                        status=f.get("status", "modified"),
                        additions=f.get("additions", 0),
                        deletions=f.get("deletions", 0),
                        patch=f.get("patch"),  # Raw diff content
                        language=self._infer_language(filename),
                    )
                )

            # 4. Construct complete PRContext object
            return PRContext(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                pr_title=pr_data.get("title", ""),
                pr_description=pr_data.get("body") or "",
                author=pr_data.get("user", {}).get("login", "unknown"),
                base_branch=pr_data.get("base", {}).get("ref", "main"),
                head_branch=pr_data.get("head", {}).get("ref", ""),
                head_sha=pr_data.get("head", {}).get("sha", ""),
                changed_files=changed_files,
            )

    async def post_pr_comment(
        self, repo_full_name: str, pr_number: int, comment_body: str
    ) -> dict:
        """Posts a Markdown review comment to the Pull Request on GitHub."""
        comment_url = (
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"
        )
        logger.info(f"Posting automated comment to {comment_url}")

        payload = {"body": comment_body}
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0,follow_redirects=True) as client:
            res = await client.post(comment_url, json=payload)
            res.raise_for_status()
            return res.json()
