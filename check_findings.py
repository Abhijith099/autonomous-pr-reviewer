import asyncio
from sqlalchemy import text
from app.db.session import engine


async def check():
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                """
                SELECT agent_name, severity, file_path, issue, recommendation, created_at 
                FROM findings 
                ORDER BY created_at DESC 
                LIMIT 4;
                """
            )
        )
        rows = res.fetchall()

        print(f"\n{'='*20} LATEST FINDINGS IN NEON DB ({len(rows)}) {'='*20}")
        for r in rows:
            print(f"\nAgent:          {r[0].upper()}")
            print(f"Severity:       {r[1]}")
            print(f"File:           {r[2]}")
            print(f"Issue:          {r[3]}")
            print(f"Recommendation: {r[4]}")
            print(f"Logged At:      {r[5]}")
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(check())
