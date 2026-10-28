import json
import logging
from groq import AsyncGroq
from app.config import settings
from app.schemas import ChangedFile, Finding, AgentFindingsResponse

logger = logging.getLogger("pr_reviewer.security_agent")

SECURITY_AGENT_SYSTEM_PROMPT = """You are a senior security code reviewer.
Your job is to identify concrete, evidence-based security risks in the provided pull request git diff.

Focus specifically on:
1. Hardcoded secrets, API keys, passwords, database credentials, or tokens.
2. SQL injection risks (string formatting or concatenation in queries).
3. Command injection or unsafe execution (eval, exec, unsanitized subprocess).
4. Insecure deserialization (e.g., pickle, unsafe YAML loading).
5. Missing authentication or authorization checks.
6. Path traversal or unsafe file operations with user input.

Rules:
- Review ONLY the changed lines in the diff and surrounding context.
- Do NOT hallucinate issues that are not evident in the diff.
- Do NOT comment on formatting, variable naming, or general code style.
- If no security risk exists in the diff, return an empty findings list: {"findings": []}.

You MUST return a JSON object strictly matching this schema:
{
  "findings": [
    {
      "agent": "security",
      "severity": "critical",
      "category": "security",
      "file": "path/to/file.py",
      "line_hint": "12",
      "issue": "Concise description of the security vulnerability",
      "recommendation": "Concrete steps to fix it",
      "confidence": 0.95
    }
  ]
}

Valid values for severity: "critical", "high", "medium", "low", "info".
Confidence must be a number between 0.0 and 1.0.
"""

#prompt 


class SecurityAgent:
    """Agent dedicated to discovering security vulnerabilities in code diffs."""

    def __init__(self, model: str = "qwen/qwen3.8-27b"): #init AsyncGRoq using groq key from .env
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = model

    def _format_diff_for_prompt(self, files: list[ChangedFile]) -> str: # fromatiing diff into txt
        """Formats file diffs into a clean text block for the LLM."""
        diff_text = []
        for f in files:
            # Skip files without a patch (e.g. deleted or binary files)
            if not f.patch:
                continue
            diff_text.append(f"--- File: {f.filename} ({f.language or 'unknown'}) ---")
            diff_text.append(f.patch)
            diff_text.append("\n" + "=" * 40 + "\n")

        return "\n".join(diff_text)

    async def review(self, files: list[ChangedFile]) -> list[Finding]:
        """Runs the security analysis across the changed files."""
        formatted_diff = self._format_diff_for_prompt(files)

        if not formatted_diff.strip():
            logger.info("No patch content to review for security.")
            return []

        user_prompt = f"""Review the following pull request diff for security vulnerabilities:

{formatted_diff}

Identify concrete security issues and return structured findings matching the schema.
"""

        try:
            logger.info(f"Calling Security Agent model ({self.model})...")
            # Groq structured outputs with JSON schema enforcement
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SECURITY_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Low temperature for deterministic, factual output
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content or "{}"
            parsed_json = json.loads(raw_content)

            # If model returned {'findings': [...]}, parse with Pydantic
            if "findings" in parsed_json:
                validated = AgentFindingsResponse(**parsed_json)
                findings = validated.findings
            elif isinstance(parsed_json, list):
                findings = [Finding(**item) for item in parsed_json]
            else:
                findings = []

            # Ensure all findings are tagged with agent='security'
            for finding in findings:
                finding.agent = "security"
                finding.category = "security"

            logger.info(f"Security Agent produced {len(findings)} finding(s).")
            return findings

        except Exception as e:
            logger.error(f"Security Agent execution failed: {e}", exc_info=True)
            return []
