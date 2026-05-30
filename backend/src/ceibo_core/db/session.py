from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ceibo_core.core.config import settings
from ceibo_core.db.models import Base
from ceibo_core.models.schemas import PersistenceHealth

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    if not settings.persistence_enabled:
        return
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def persistence_health() -> PersistenceHealth:
    safe_url = _safe_database_url(settings.database_url)
    if not settings.persistence_enabled:
        return PersistenceHealth(
            enabled=False,
            available=False,
            database_url_safe=safe_url,
            error="persistence disabled",
        )
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
            tables = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_table_names()
            )
        return PersistenceHealth(
            enabled=True,
            available=True,
            database_url_safe=safe_url,
            tables=sorted(tables),
        )
    except SQLAlchemyError as exc:
        return PersistenceHealth(
            enabled=True,
            available=False,
            database_url_safe=safe_url,
            error=str(exc),
        )


async def get_db():
    async with SessionLocal() as session:
        yield session


def _safe_database_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", maxsplit=1)
    _, host = rest.rsplit("@", maxsplit=1)
    return f"{scheme}://***:***@{host}"
