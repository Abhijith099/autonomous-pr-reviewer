import asyncio
from app.agents.quality_agent import QualityAgent
from app.schemas import ChangedFile


async def main():
    print("Testing QualityAgent...")

    # 1. Create mock changed files with intentional quality bugs
    # Bug 1: swallowing exception silently ('except Exception: pass')
    # Bug 2: calling async function without 'await'
    mock_patch = """
@@ -10,6 +10,14 @@ def process_user_data(user_id: int):
+async def handle_payment(order_id: str):
+    try:
+        # Bug 1: missing await on async call
+        result = charge_credit_card(order_id)
+    except Exception:
+        # Bug 2: swallowing error silently with no logging or recovery
+        pass
+    return {"status": "ok"}
"""

    mock_files = [
        ChangedFile(
            filename="app/billing/payments.py",
            status="modified",
            additions=9,
            deletions=0,
            patch=mock_patch.strip(),
            language="python",
        )
    ]

    # 2. Instantiate and run QualityAgent
    agent = QualityAgent()
    findings = await agent.review(mock_files)

    # 3. Display Results
    print(f"\n--- Quality Agent Results: {len(findings)} Finding(s) ---")
    for f in findings:
        print(f"[{f.severity.upper()}] {f.file}:{f.line_hint or 'N/A'}")
        print(f"  Agent:          {f.agent}")
        print(f"  Category:       {f.category}")
        print(f"  Issue:          {f.issue}")
        print(f"  Recommendation: {f.recommendation}")
        print(f"  Confidence:     {int(f.confidence * 100)}%")
        print("-" * 50)

    # 4. Assertions to confirm behavior
    assert len(findings) > 0, "Expected at least 1 quality finding!"
    assert all(f.agent == "quality" for f in findings), "All findings must have agent='quality'"
    assert all(f.category == "quality" for f in findings), "All findings must have category='quality'"

    print("\nAll quality agent assertions passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())