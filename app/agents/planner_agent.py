import json #standard python module for parsing json string retured by the groq llm
import logging #standard python module used to output infomative log messages and error logs during execution
from groq import AsyncGroq
from app.config import settings
from app.schemas import PRContext, PlannerDecision

logger = logging.getLogger(__name__)  #creats logger scoped to this modyle so we can trace when planning starts succeceds or encounters and issue.

PLANNER_SYSTEM_PROMPT = """You are an expert Lead Software Architect and PR Triage Planner.
Your role is to analyze a Pull Request's metadata and list of changed files, then decide:
1. Which files MUST be reviewed by automated agents (security, code quality, performance).
2. Which files SHOULD BE SKIPPED (documentation, lockfiles, generated assets, static images, simple configs).
3. The key architectural focus areas for this PR (e.g., authentication, database queries, API endpoints, error handling).

Rules for Triage:
- ALWAYS SKIP: markdown docs (*.md), text notes (*.txt), lock files (*.lock, package-lock.json), image/binary assets, license files.
- ALWAYS REVIEW: application source code (.py, .js, .ts, .go, .rs), SQL migrations, auth/security configs, workflow/pipeline changes if touching deployment/secrets.
- Focus Areas: Provide 2-5 clear, concise focus bullet points highlighting what the review agents should pay extra attention to.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "files_to_review": ["path/to/file1.py", "path/to/file2.ts"],
  "files_to_skip": ["README.md", "poetry.lock"],
  "focus_areas": ["Authentication logic in file1.py", "Database migration safety in file2.ts"]
}
Do not include markdown formatting or commentary outside the JSON object.
"""

#instructs the LLM


class PlannerAgent:   #Declares the agent responsibel for PR planning and triage
    def __init__(self, model: str = "qwen/qwen3.8-27b"):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = model

    async def plan(self, pr_context: PRContext) -> PlannerDecision:
        files_summary = [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
            }
            for f in pr_context.changed_files
        ]

        user_content = (
            f"Pull Request Title: {pr_context.pr_title}\n"
            f"Pull Request Description: {pr_context.pr_description or 'No description provided.'}\n\n"
            f"Changed Files List:\n{json.dumps(files_summary, indent=2)}\n\n"
            "Triage these files into files_to_review and files_to_skip, and identify key focus_areas."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw_text = response.choices[0].message.content or "{}"
            parsed_json = json.loads(raw_text)

            return PlannerDecision(**parsed_json)

        except Exception as e:
            logger.error(f"PlannerAgent failed to generate plan: {e}. Falling back to default plan.")
            all_files = [f.filename for f in pr_context.changed_files]
            return PlannerDecision(
                files_to_review=all_files,
                files_to_skip=[],
                focus_areas=["General review across all changed files (planner fallback)."]
            )