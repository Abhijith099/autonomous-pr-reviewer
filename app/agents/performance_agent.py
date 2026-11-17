import json
import logging
from groq import AsyncGroq
from app.config import settings
from app.schemas import ChangedFile, Finding, AgentFindingsResponse

logger = logging.getLogger("pr_reviewer.performance_agent")

PERFORMANCE_AGENT_SYSTEM_PROMPT = """You are a Principal Systems Architect and Database Performance Engineer.
Your role is to identify concrete, objective performance bottlenecks, memory bloat, and algorithmic inefficiencies in the provided pull request git diff.

Focus specifically on:
1. Database & ORM Inefficiencies:
   - N+1 query patterns (querying inside loops).
   - Missing query limits or unpaginated collection fetching.
   - Missing indices on columns used frequently in WHERE filters, JOINs, or ORDER BY in new SQL migrations.
   - Loading full ORM models when only specific columns are needed.
2. Async Event Loop Blocking:
   - Synchronous blocking I/O (e.g. `requests.get`, `time.sleep`, heavy filesystem access) inside `async def` functions.
   - Heavy CPU-bound computation executed directly on the async event loop without delegating to a thread/process pool.
3. Memory Management & Resource Leaks:
   - Reading entire large files into memory at once instead of streaming or chunking.
   - Creating unbounded in-memory caches or accumulators that grow without limit.
4. Algorithmic Complexity:
   - O(N^2) or worse nested iterations over large collections that could be O(N) using HashMaps/Sets.
   - Redundant serialization/deserialization cycles inside hot loops.

Rules:
- Review ONLY the changed lines in the diff and their immediate context.
- Do NOT hallucinate issues that are not evident in the diff.
- Do NOT comment on trivial micro-optimizations that offer negligible real-world benefit.
- If no performance bottlenecks exist in the diff, return an empty findings list: {"findings": []}.
- Output ONLY raw JSON starting immediately with '{' and ending with '}'. Do NOT include introductory thoughts, conversational text, or markdown codeblocks outside the JSON.

You MUST return a JSON object strictly matching this schema:
{
  "findings": [
    {
      "agent": "performance",
      "severity": "high",
      "category": "performance",
      "file": "path/to/file.py",
      "line_hint": "42",
      "issue": "Concise description of the performance bottleneck (e.g. N+1 query, blocking async sleep)",
      "recommendation": "Concrete, actionable optimization steps",
      "confidence": 0.90
    }
  ]
}

Valid values for severity: "critical", "high", "medium", "low", "info".
Confidence must be a number between 0.0 and 1.0.
"""


class PerformanceAgent:
    """Agent dedicated to identifying database, memory, and algorithmic performance bottlenecks."""

    def __init__(self, model: str = "qwen/qwen3.8-27b"):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = model

    def _format_diff_for_prompt(self, files: list[ChangedFile]) -> str:
        """Formats file diffs into a clean text block for the LLM."""
        diff_text = []
        for f in files:
            if not f.patch:
                continue
            diff_text.append(f"--- File: {f.filename} ({f.language or 'unknown'}) ---")
            diff_text.append(f.patch)
            diff_text.append("\n" + "=" * 40 + "\n")

        return "\n".join(diff_text)

    async def review(self, files: list[ChangedFile]) -> list[Finding]:
        """Runs the performance analysis across the changed files."""
        formatted_diff = self._format_diff_for_prompt(files)

        if not formatted_diff.strip():
            logger.info("No patch content to review for performance.")
            return []

        user_content = (
            "Analyze the following pull request git diff strictly for performance bottlenecks, "
            "database inefficiencies (like N+1 queries), blocking calls, or excessive memory usage.\n\n"
            f"{formatted_diff}"
        )

        logger.info(f"Calling Performance Agent model ({self.model})...")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PERFORMANCE_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,  # Low temperature for deterministic analysis
                response_format={"type": "json_object"},
            )

            raw_text = response.choices[0].message.content or "{}"
            parsed_response = AgentFindingsResponse.model_validate_json(raw_text)

            logger.info(
                f"Performance Agent produced {len(parsed_response.findings)} finding(s)."
            )
            return parsed_response.findings

        except Exception as e:
            logger.error(f"Performance Agent execution failed: {e}", exc_info=True)
            return []
