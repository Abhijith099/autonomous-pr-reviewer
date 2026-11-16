import json # standary python modyle used to parse th JDON string response frmo the GRoq LLM
import logging # standard python frameword to log messages
from groq import AsyncGroq  # asynchronous groq client for non-blocking LLM calls
from app.config import settings    # import our application setting onject to read groq_api_key
from app.schemas import ChangedFile, Finding, AgentFindingsResponse  # represents each fiels attributes changed fils 

logger = logging.getLogger("pr_reviewer.quality_agent")  # creates a logger that specifically for this agent

QUALITY_AGENT_SYSTEM_PROMPT = """You are a Principal Software Engineer and Code Quality Reviewer.
Your role is to identify concrete, objective code quality, maintainability, and reliability bugs in the provided pull request git diff.

Focus specifically on:
1. Error handling: Unhandled exceptions, swallowing errors without logging (`except: pass`), missing validation on boundary inputs.
2. Async & Concurrency issues: Missing `await` keywords, unawaited coroutines, blocking synchronous calls in async event loops.
3. Resource leaks: Unclosed connections, missing context managers (`with`, `async with`), unreleased locks.
4. Logic errors: Off-by-one errors, broken boolean logic, unreachable dead code, mutating collections while iterating.
5. Code health: Blatant code smells, confusing edge cases, or broken contracts.

Rules:
- Review ONLY the changed lines in the diff and their immediate context.
- Do NOT hallucinate issues that are not evident in the diff.
- Do NOT comment on trivial styling, nitpicks, indentation, or opinions on variable names (linters/formatters handle those).
- If no quality or reliability issues exist in the diff, return an empty findings list: {"findings": []}.
- Output ONLY raw JSON starting immediately with '{' and ending with '}'. Do NOT include introductory thoughts, conversational text, or markdown codeblocks outside the JSON.

You MUST return a JSON object strictly matching this schema:
{
  "findings": [
    {
      "agent": "quality",
      "severity": "medium",
      "category": "quality",
      "file": "path/to/file.py",
      "line_hint": "42",
      "issue": "Concise description of the code quality or reliability defect",
      "recommendation": "Concrete steps to fix or refactor it",
      "confidence": 0.90
    }
  ]
}

Valid values for severity: "critical", "high", "medium", "low", "info".
Confidence must be a number between 0.0 and 1.0.
"""




class QualityAgent:
    """Agent dedicated to discovering code quality, reliability, and logic issues in git diffs."""

    def __init__(self, model: str = "qwen/qwen3.8-27b"): #Initializes the client with settings.GROQ_API_KEY and sets the model.
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = model

    def _format_diff_for_prompt(self, files: list[ChangedFile]) -> str: # iterate through the changed file and buils a clear readable diff text steperate by dividers...
        """Formats file diffs into a clean text block for the LLM."""
        diff_text = []
        for f in files:
            if not f.patch:
                continue
            diff_text.append(f"--- File: {f.filename} ({f.language or 'unknown'}) ---")
            diff_text.append(f.patch)
            diff_text.append("\n" + "=" * 40 + "\n")

        return "\n".join(diff_text)

    async def review(self, files: list[ChangedFile]) -> list[Finding]: #entry point of agent 
        """Runs the code quality analysis across the changed files."""
        formatted_diff = self._format_diff_for_prompt(files)

        if not formatted_diff.strip():
            logger.info("No patch content to review for code quality.")
            return []   # this returns if there is no code to revirew saveas an unneccssary llm api call 

        user_prompt = f"""Review the following pull request diff for code quality, reliability, and logic issues:

{formatted_diff}

Identify concrete code quality defects and return structured findings matching the schema.
Output ONLY the JSON object starting with '{{' and ending with '}}'. If no issues, return {{"findings": []}}.
"""

        try:
            logger.info(f"Calling Quality Agent model ({self.model})...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUALITY_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content or "{}"
            parsed_json = json.loads(raw_content)

            if "findings" in parsed_json:
                validated = AgentFindingsResponse(**parsed_json)
                findings = validated.findings
            elif isinstance(parsed_json, list):
                findings = [Finding(**item) for item in parsed_json]
            else:
                findings = []

            for finding in findings:
                finding.agent = "quality"
                finding.category = "quality"

            logger.info(f"Quality Agent produced {len(findings)} finding(s).")
            return findings

        except Exception as e:
            logger.error(f"Quality Agent execution failed: {e}", exc_info=True)
            return []#Resilient error handling. If an API timeout or network error occurs, it logs the error and returns an empty list, allowing the rest of the PR review to proceed without crashing.