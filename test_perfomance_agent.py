import asyncio
from app.agents.performance_agent import PerformanceAgent
from app.schemas import ChangedFile

mock_diff = """--- a/app/services/reports.py
+++ b/app/services/reports.py
@@ -1,15 +1,18 @@
+import time
+from app.db import get_db
+
+async def generate_user_reports(users, db):
+    reports = []
+    for user in users:
+        # N+1 Query: hitting DB inside a loop for each user!
+        orders = await db.execute(f"SELECT * FROM orders WHERE user_id = {user.id}")
+        
+        # Blocking event loop: synchronous sleep inside async function!
+        time.sleep(1)
+        
+        reports.append({"user": user.name, "orders": orders.fetchall()})
+    return reports
"""

mock_file = ChangedFile(
    filename="app/services/reports.py",
    status="modified",
    additions=14,
    deletions=0,
    patch=mock_diff,
    language="python"
)
async def run_test():
    print("Testing PerformanceAgent...\n")
    agent = PerformanceAgent()
    
    # Run the agent on our mock file
    findings = await agent.review([mock_file])
    
    print(f"--- Performance Agent Results: {len(findings)} Finding(s) ---")
    for f in findings:
        print(f"[{f.severity.upper()}] {f.file}:{f.line_hint or 'N/A'}")
        print(f"  Agent:          {f.agent}")
        print(f"  Category:       {f.category}")
        print(f"  Issue:          {f.issue}")
        print(f"  Recommendation: {f.recommendation}")
        print(f"  Confidence:     {int(f.confidence * 100)}%")
        print("-" * 50)
        
    # Assertions to ensure our agent behaves correctly:
    assert len(findings) > 0, "Agent should have detected performance issues!"
    assert all(f.agent == "performance" for f in findings), "All findings must belong to 'performance' agent!"
    print("\n✅ All assertions passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_test())