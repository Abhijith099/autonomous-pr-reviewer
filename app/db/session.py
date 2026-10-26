from collections.abc import AsyncGenerator 
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker,create_async_engine

from app.config import settings

#creates async engine with neon ssl requirements
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,#sets to true if you want to see all raw sql queries in console
    pool_pre_ping=True,#Automatically checks if the connection is alive before using
    connect_args={"ssl": "require"} # tells asyncpg to use ssl for neon
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession,None]:
    """Dependency helper to yield async DB sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()