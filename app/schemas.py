from typing import Literal
from pydantic import BaseModel, Field
# 1. Represents an individual file changed in a PR
class ChangedFile(BaseModel):
    filename: str
    status: Literal["added", "modified", "removed", "renamed"]
    additions: int = 0
    deletions: int = 0
    patch: str | None = None  # Raw diff patch from GitHub (None if binary/empty)
    language: str | None = None
# 2. Represents a single finding produced by an AI Agent
class Finding(BaseModel):
    agent: Literal["planner", "security", "quality", "performance", "testing", "summariser"]
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str = "general"
    file: str
    line_hint: str | None = None
    issue: str
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
# 3. Agent Structured Output container (used for Groq/LLM response parsing)
class AgentFindingsResponse(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
# 4. Context of the Pull Request extracted from GitHub API
class PRContext(BaseModel):
    repo_full_name: str
    pr_number: int
    pr_title: str
    pr_description: str | None = ""
    author: str
    base_branch: str
    head_branch: str
    head_sha: str
    changed_files: list[ChangedFile] = Field(default_factory=list)
# 5. Shared State across the entire review workflow
class ReviewState(BaseModel):
    pr: PRContext
    review_plan: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    final_comment: str = ""
    status: Literal[
        "queued", "fetching", "planning", "reviewing",
        "summarising", "commented", "completed", "failed", "skipped"
    ] = "queued"
    error_message: str | None = None