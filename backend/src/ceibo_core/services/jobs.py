from collections import deque
from datetime import UTC, datetime
import asyncio
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import LongRunningJob
from ceibo_core.models.schemas import (
    JobKind,
    JobStatus,
    LongRunningJobRecord,
    LongRunningJobRequest,
)
from ceibo_core.services.evaluation_harness import evaluation_harness_service

logger = structlog.get_logger()


class LongRunningJobService:
    def __init__(self) -> None:
        self._jobs: dict[str, LongRunningJobRecord] = {}
        self._recent_ids: deque[str] = deque(maxlen=120)

    async def enqueue(
        self,
        db: AsyncSession | None,
        request: LongRunningJobRequest,
    ) -> LongRunningJobRecord:
        record = LongRunningJobRecord(
            kind=request.kind,
            title=request.title,
            user_id=request.user_id,
            task_id=request.task_id,
            metadata=request.metadata,
        )
        await self._save(db, record)
        return record

    async def run(
        self,
        db: AsyncSession | None,
        job_id: str,
    ) -> LongRunningJobRecord:
        record = await self.get(db, job_id)
        if record is None:
            raise ValueError(f"Job not found: {job_id}")
        if record.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return record
        try:
            record = await self._update(
                db,
                record,
                status=JobStatus.RUNNING,
                progress=10,
                current_step="preparing",
            )
            await asyncio.sleep(0)
            record = await self._update(db, record, progress=35, current_step="executing")
            result = await self._execute(record)
            record = await self._update(
                db,
                record,
                status=JobStatus.COMPLETED,
                progress=100,
                current_step="completed",
                result=result,
            )
            return record
        except Exception as exc:
            logger.warning("long_running_job_failed", job_id=job_id, error=str(exc))
            return await self._update(
                db,
                record,
                status=JobStatus.FAILED,
                current_step="failed",
                error=str(exc),
            )

    async def run_background(self, job_id: str) -> None:
        if not settings.persistence_enabled:
            await self.run(None, job_id)
            return
        from ceibo_core.db.session import SessionLocal

        async with SessionLocal() as db:
            await self.run(db, job_id)

    async def get(
        self,
        db: AsyncSession | None,
        job_id: str,
    ) -> LongRunningJobRecord | None:
        if settings.persistence_enabled and db is not None:
            try:
                record = await db.get(LongRunningJob, job_id)
                if record is not None:
                    return self._from_record(record)
            except SQLAlchemyError as exc:
                logger.warning("long_running_job_get_failed", error=str(exc))
        return self._jobs.get(job_id)

    async def recent(
        self,
        db: AsyncSession | None,
        limit: int = 10,
    ) -> list[LongRunningJobRecord]:
        if settings.persistence_enabled and db is not None:
            try:
                result = await db.execute(
                    select(LongRunningJob).order_by(LongRunningJob.created_at.desc()).limit(limit)
                )
                return [self._from_record(record) for record in result.scalars().all()]
            except SQLAlchemyError as exc:
                logger.warning("long_running_job_list_failed", error=str(exc))
        return [self._jobs[job_id] for job_id in list(self._recent_ids)[:limit] if job_id in self._jobs]

    async def _execute(self, record: LongRunningJobRecord) -> dict[str, Any]:
        if record.kind == JobKind.EVALUATION:
            report = await evaluation_harness_service.run()
            return {
                "evaluation_run_id": report.run_id,
                "average_score": report.average_score,
                "status": report.status,
            }
        return {
            "message": "job completed",
            "kind": record.kind.value,
            "title": record.title,
        }

    async def _save(
        self,
        db: AsyncSession | None,
        record: LongRunningJobRecord,
    ) -> None:
        self._jobs[record.job_id] = record
        if record.job_id not in self._recent_ids:
            self._recent_ids.appendleft(record.job_id)
        if not settings.persistence_enabled or db is None:
            return
        try:
            db.add(
                LongRunningJob(
                    id=record.job_id,
                    kind=record.kind.value,
                    title=record.title,
                    status=record.status.value,
                    progress=record.progress,
                    current_step=record.current_step,
                    user_id=record.user_id,
                    task_id=record.task_id,
                    result=record.result,
                    error=record.error,
                    job_metadata=record.metadata,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("long_running_job_save_failed", error=str(exc))

    async def _update(
        self,
        db: AsyncSession | None,
        record: LongRunningJobRecord,
        **changes: Any,
    ) -> LongRunningJobRecord:
        updated = record.model_copy(update={**changes, "updated_at": datetime.now(UTC)})
        self._jobs[updated.job_id] = updated
        if not settings.persistence_enabled or db is None:
            return updated
        try:
            db_record = await db.get(LongRunningJob, updated.job_id)
            if db_record is not None:
                db_record.status = updated.status.value
                db_record.progress = updated.progress
                db_record.current_step = updated.current_step
                db_record.result = updated.result
                db_record.error = updated.error
                db_record.updated_at = updated.updated_at
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("long_running_job_update_failed", error=str(exc))
        return updated

    def _from_record(self, record: LongRunningJob) -> LongRunningJobRecord:
        return LongRunningJobRecord(
            job_id=record.id,
            kind=JobKind(record.kind),
            title=record.title,
            status=JobStatus(record.status),
            progress=record.progress,
            current_step=record.current_step,
            user_id=record.user_id,
            task_id=record.task_id,
            result=dict(record.result or {}),
            error=record.error,
            metadata=dict(record.job_metadata or {}),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


long_running_job_service = LongRunningJobService()
