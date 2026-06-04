from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.async_database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def reset_schema():
    """Full wipe + recreate, robust to orphan tables.

    `Base.metadata.drop_all` only drops tables it knows about, in FK order — but this
    DB still carries tables from the OLD restaurant schema (reservations/orders/faqs)
    whose foreign keys reference `agents`. Those orphans aren't in Base.metadata, so a
    model-only drop_all fails with DependentObjectsStillExistError. Dropping and
    recreating the `public` schema clears everything (orphans included) reliably."""
    import app.models.models  # noqa: F401 — register all models on Base before create_all
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
