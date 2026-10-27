import asyncio
from pathlib import Path
from sqlalchemy import text
from app.db.session import engine


async def init_database():
    schema_path = Path("app/db/schema.sql")
    if not schema_path.exists():
        print(f"Error: Could not find {schema_path}")
        return

    print("Reading schema.sql...")
    sql_script = schema_path.read_text(encoding="utf-8")

    print("Connecting to Neon PostgreSQL...")
    # Use raw asyncpg connection to execute multi-command SQL script
    async with engine.connect() as conn:
        print("Executing schema setup...")
        # conn.connection.dbapi_connection is the underlying asyncpg connection
        raw_conn = await conn.get_raw_connection()
        await raw_conn.driver_connection.execute(sql_script)
        print("Schema executed successfully!")

        # Verify created tables
        result = await conn.execute(
            text(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """
            )
        )
        tables = [row[0] for row in result.fetchall()]
        print("\nVerified Tables in Neon Database:")
        for t in tables:
            print(f"  - {t}")

    await engine.dispose()
    print("\nDatabase initialization complete and verified!")


if __name__ == "__main__":
    asyncio.run(init_database())
