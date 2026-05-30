from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ceibo_core.core.config import settings
from ceibo_core.db.models import Base

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    if not settings.persistence_enabled:
        return
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db():
    async with SessionLocal() as session:
        yield session
