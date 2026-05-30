import hashlib
import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import DatasetVersion, ModelVersion
from ceibo_core.models.schemas import (
    DatasetVersionRecord,
    DatasetVersionRequest,
    ModelVersionRecord,
    ModelVersionRequest,
    ModelVersionStatus,
    RegistryOverview,
)

logger = structlog.get_logger()


class ModelRegistryService:
    def __init__(self) -> None:
        self._fallback_datasets: deque[DatasetVersionRecord] = deque(maxlen=100)
        self._fallback_models: deque[ModelVersionRecord] = deque(maxlen=100)

    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[4]

    async def bootstrap_seed_registry(self, db: AsyncSession | None = None) -> RegistryOverview:
        datasets_dir = self.project_root() / "training" / "datasets"
        dataset_records: list[DatasetVersionRecord] = []
        for path in sorted(datasets_dir.glob("*.jsonl")):
            dataset_records.append(
                await self.register_dataset(
                    db,
                    DatasetVersionRequest(
                        name=path.stem,
                        path=str(path.relative_to(self.project_root())),
                        source="bootstrap",
                        metadata={"kind": "jsonl"},
                    ),
                )
            )

        active_model = await self.register_model(
            db,
            ModelVersionRequest(
                name=settings.ceibo_engine_model_id,
                base_model=settings.default_llm_provider,
                status=ModelVersionStatus.ACTIVE,
                metrics={"provider": settings.default_llm_provider, "mode": settings.ceibo_engine_mode},
                metadata={"kind": "local_rules_engine"},
            ),
        )
        return RegistryOverview(
            datasets=dataset_records,
            models=[active_model],
            active_model=active_model,
        )

    async def register_dataset(
        self,
        db: AsyncSession | None,
        request: DatasetVersionRequest,
    ) -> DatasetVersionRecord:
        path = self._resolve_project_path(request.path)
        if not path.exists():
            raise ValueError(f"Dataset not found: {request.path}")
        record = DatasetVersionRecord(
            version_id=f"ds-{uuid4().hex[:12]}",
            name=request.name,
            path=str(path),
            sha256=self._sha256(path),
            examples=self._count_jsonl(path),
            source=request.source,
            metadata=request.metadata,
            created_at=datetime.now(UTC),
        )
        self._fallback_datasets.appendleft(record)

        if settings.persistence_enabled and db is not None:
            try:
                db.add(
                    DatasetVersion(
                        id=record.version_id,
                        name=record.name,
                        path=record.path,
                        sha256=record.sha256,
                        examples=record.examples,
                        source=record.source,
                        dataset_metadata=record.metadata,
                        created_at=record.created_at,
                    )
                )
                await db.commit()
            except SQLAlchemyError as exc:
                await db.rollback()
                logger.warning("dataset_version_register_failed", error=str(exc))
        return record

    async def register_model(
        self,
        db: AsyncSession | None,
        request: ModelVersionRequest,
    ) -> ModelVersionRecord:
        if request.status == ModelVersionStatus.ACTIVE:
            await self._deactivate_active_model(db)

        record = ModelVersionRecord(
            version_id=f"model-{uuid4().hex[:12]}",
            name=request.name,
            base_model=request.base_model,
            adapter_path=request.adapter_path,
            dataset_version_id=request.dataset_version_id,
            status=request.status,
            metrics=request.metrics,
            metadata=request.metadata,
            created_at=datetime.now(UTC),
        )
        self._fallback_models.appendleft(record)

        if settings.persistence_enabled and db is not None:
            try:
                db.add(
                    ModelVersion(
                        id=record.version_id,
                        name=record.name,
                        base_model=record.base_model,
                        adapter_path=record.adapter_path,
                        dataset_version_id=record.dataset_version_id,
                        status=record.status.value,
                        metrics=record.metrics,
                        model_metadata=record.metadata,
                        created_at=record.created_at,
                    )
                )
                await db.commit()
            except SQLAlchemyError as exc:
                await db.rollback()
                logger.warning("model_version_register_failed", error=str(exc))
        return record

    async def overview(self, db: AsyncSession | None, limit: int = 20) -> RegistryOverview:
        datasets = await self.list_datasets(db, limit=limit)
        models = await self.list_models(db, limit=limit)
        active_model = next((model for model in models if model.status == ModelVersionStatus.ACTIVE), None)
        return RegistryOverview(datasets=datasets, models=models, active_model=active_model)

    async def list_datasets(
        self,
        db: AsyncSession | None,
        limit: int = 20,
    ) -> list[DatasetVersionRecord]:
        if not settings.persistence_enabled or db is None:
            return list(self._fallback_datasets)[:limit]
        try:
            result = await db.execute(
                select(DatasetVersion).order_by(DatasetVersion.created_at.desc()).limit(limit)
            )
            return [self._dataset_from_record(record) for record in result.scalars().all()]
        except SQLAlchemyError as exc:
            logger.warning("dataset_version_list_failed", error=str(exc))
            return list(self._fallback_datasets)[:limit]

    async def list_models(
        self,
        db: AsyncSession | None,
        limit: int = 20,
    ) -> list[ModelVersionRecord]:
        if not settings.persistence_enabled or db is None:
            return list(self._fallback_models)[:limit]
        try:
            result = await db.execute(
                select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(limit)
            )
            return [self._model_from_record(record) for record in result.scalars().all()]
        except SQLAlchemyError as exc:
            logger.warning("model_version_list_failed", error=str(exc))
            return list(self._fallback_models)[:limit]

    async def _deactivate_active_model(self, db: AsyncSession | None) -> None:
        self._fallback_models = deque(
            [
                model.model_copy(update={"status": ModelVersionStatus.APPROVED})
                if model.status == ModelVersionStatus.ACTIVE
                else model
                for model in self._fallback_models
            ],
            maxlen=100,
        )
        if not settings.persistence_enabled or db is None:
            return
        try:
            result = await db.execute(
                select(ModelVersion).where(ModelVersion.status == ModelVersionStatus.ACTIVE.value)
            )
            for model in result.scalars().all():
                model.status = ModelVersionStatus.APPROVED.value
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("active_model_deactivate_failed", error=str(exc))

    def _resolve_project_path(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root() / path
        return path.resolve()

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _count_jsonl(self, path: Path) -> int:
        total = 0
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
        return total

    def _dataset_from_record(self, record: DatasetVersion) -> DatasetVersionRecord:
        return DatasetVersionRecord(
            version_id=record.id,
            name=record.name,
            path=record.path,
            sha256=record.sha256,
            examples=record.examples,
            source=record.source,
            metadata=record.dataset_metadata,
            created_at=record.created_at,
        )

    def _model_from_record(self, record: ModelVersion) -> ModelVersionRecord:
        return ModelVersionRecord(
            version_id=record.id,
            name=record.name,
            base_model=record.base_model,
            adapter_path=record.adapter_path,
            dataset_version_id=record.dataset_version_id,
            status=ModelVersionStatus(record.status),
            metrics=record.metrics,
            metadata=record.model_metadata,
            created_at=record.created_at,
        )


model_registry_service = ModelRegistryService()
