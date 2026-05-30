from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

from ceibo_core.api.routes.agents import router as agents_router
from ceibo_core.api.routes.chat import router as chat_router
from ceibo_core.api.routes.devcore import router as devcore_router
from ceibo_core.api.routes.engine import router as engine_router
from ceibo_core.api.routes.health import router as health_router
from ceibo_core.api.routes.memory import router as memory_router
from ceibo_core.api.routes.status import router as status_router
from ceibo_core.api.routes.tasks import router as tasks_router
from ceibo_core.api.routes.ws import router as ws_router
from ceibo_core.core.config import settings
from ceibo_core.core.logging import configure_logging
from ceibo_core.db.session import init_db
from ceibo_core.services.event_bus import event_bus

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as exc:  # pragma: no cover - local dev may run without Postgres
        logger.warning("database_unavailable", error=str(exc))
    await event_bus.connect()
    yield
    await event_bus.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="CEIBO CORE multi-agent AI platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(agents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(devcore_router, prefix="/api/v1")
app.include_router(engine_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(status_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")

Instrumentator().instrument(app).expose(app)
