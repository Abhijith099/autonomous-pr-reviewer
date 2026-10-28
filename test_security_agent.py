import asyncio
from app.agents.security_agent import SecurityAgent
from app.schemas import ChangedFile

# 1. Simulate a git diff with intentional security bugs
mock_vulnerable_files = [
    ChangedFile(
        filename="app/config.py",
        status="modified",
        additions=2,
        deletions=0,
        language="python",
        patch="""@@ -5,2 +5,4 @@
+ # Production credentials
+ AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
""",
    ),
    ChangedFile(
        filename="app/database.py",
        status="modified",
        additions=5,
        deletions=1,
        language="python",
        patch="""@@ -20,4 +20,6 @@ def get_user_by_name(username: str):
-    # Fetch user safely
+    # Dynamically build SQL query
+    query = f"SELECT * FROM users WHERE username = '{username}'"
+    return db.execute(query)
""",
    ),
]


async def run_test():
    print("Initializing Security Agent...")
    agent = SecurityAgent()

    print("Analyzing vulnerable diff with Groq...")
    findings = await agent.review(mock_vulnerable_files)

    print(f"\nDiscovered {len(findings)} security finding(s):\n")
    for i, finding in enumerate(findings, 1):
        print(f"Finding #{i}:")
        print(f"  File:           {finding.file}")
        print(f"  Severity:       {finding.severity.upper()}")
        print(f"  Issue:          {finding.issue}")
        print(f"  Recommendation: {finding.recommendation}")
        print(f"  Confidence:     {finding.confidence}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(run_test())
