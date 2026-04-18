import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Example: postgresql+asyncpg://postgres:postgres@localhost:5434/deepsecurity"
    )

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Incremental column migrations (safe to re-run — IF NOT EXISTS)
        await conn.execute(text(
            "ALTER TABLE recognitionlog ADD COLUMN IF NOT EXISTS is_spoof BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE recognitionlog ADD COLUMN IF NOT EXISTS antispoof_score FLOAT"
        ))
        await conn.execute(text(
            "ALTER TABLE videorecording ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
        ))


async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
