import asyncio
from sqlalchemy import text
from app.db.session import engine


async def check():
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                """
            SELECT 
                r.full_name, 
                p.pr_number, 
                rev.status, 
                rev.latency_ms, 
                rev.total_files_changed,
                rev.created_at
            FROM review_runs rev
            JOIN pull_requests p ON p.id = rev.pull_request_id
            JOIN repositories r ON r.id = p.repository_id
            ORDER BY rev.created_at DESC 
            LIMIT 5;
        """
            )
        )
        rows = res.fetchall()
        print("\n--- Recent Review Runs in Neon DB ---")
        for row in rows:
            print(
                f"Repo: {row[0]} | PR #{row[1]} | Status: {row[2]} | Latency: {row[3]}ms | Files: {row[4]} | Created: {row[5]}"
            )


if __name__ == "__main__":
    asyncio.run(check())
