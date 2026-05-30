import structlog
from nats.aio.client import Client as NATS

from ceibo_core.core.config import settings

logger = structlog.get_logger()


class EventBus:
    def __init__(self) -> None:
        self._client = NATS()

    async def connect(self) -> None:
        if not settings.event_bus_enabled:
            logger.info("event_bus_disabled")
            return
        try:
            await self._client.connect(
                servers=[settings.nats_url],
                connect_timeout=1,
                max_reconnect_attempts=0,
            )
            logger.info("event_bus_connected", url=settings.nats_url)
        except Exception as exc:  # pragma: no cover - startup must tolerate local partial infra
            logger.warning("event_bus_unavailable", error=str(exc))

    async def publish(self, subject: str, payload: bytes) -> None:
        if not settings.event_bus_enabled:
            return
        if self._client.is_connected:
            await self._client.publish(subject, payload)

    async def close(self) -> None:
        if self._client.is_connected:
            await self._client.drain()


event_bus = EventBus()
