import asyncio
from sqlalchemy import text
from app.db.session import engine

async def fix():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE findings ALTER COLUMN agent_run_id DROP NOT NULL;"))
        print("Successfully updated database! agent_run_id can now be NULL.")

asyncio.run(fix())