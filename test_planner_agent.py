import asyncio
from app.agents.planner_agent import PlannerAgent
from app.schemas import ChangedFile, PRContext


async def main():
    print("Testing PlannerAgent...")

    # 1. Create mock changed files (mix of source code, migrations, and skippable docs/locks)
    mock_files = [
        ChangedFile(
            filename="app/auth/routes.py",
            status="modified",
            additions=45,
            deletions=10,
            patch="@@ -1,5 +1,10 @@ ...",
        ),
        ChangedFile(
            filename="app/db/migrations/002_add_users.sql",
            status="added",
            additions=20,
            deletions=0,
            patch="@@ -0,0 +1,20 @@ ...",
        ),
        ChangedFile(
            filename="README.md",
            status="modified",
            additions=5,
            deletions=2,
            patch="@@ -1,3 +1,6 @@ ...",
        ),
        ChangedFile(
            filename="poetry.lock",
            status="modified",
            additions=120,
            deletions=40,
            patch="@@ -10,6 +10,12 @@ ...",
        ),
    ]

    # 2. Create mock PRContext
        # 2. Create mock PRContext
    mock_pr = PRContext(
        repo_full_name="my-org/my-app",
        pr_number=42,
        pr_title="feat: Add user authentication endpoints and migration",
        pr_description="This PR implements JWT authentication and adds the user table migration.",
        author="alice",
        base_branch="main",
        head_branch="feat/auth",
        head_sha="abcdef123456",
        changed_files=mock_files,
    )

    # 3. Instantiate and run PlannerAgent
    planner = PlannerAgent()
    decision = await planner.plan(mock_pr)

    # 4. Display Results
    print("\n--- Planner Decision Results ---")
    print(f"Files to Review: {decision.files_to_review}")
    print(f"Files to Skip:   {decision.files_to_skip}")
    print(f"Focus Areas:     {decision.focus_areas}")

    # 5. Assertions to confirm behavior
    assert "app/auth/routes.py" in decision.files_to_review, "Expected app/auth/routes.py in files_to_review"
    assert "README.md" in decision.files_to_skip, "Expected README.md in files_to_skip"
    print("\nAll assertions passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())