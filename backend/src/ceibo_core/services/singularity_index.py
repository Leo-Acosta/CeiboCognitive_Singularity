from pathlib import Path
from collections import deque

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.core.config import settings
from ceibo_core.db.models import SingularitySnapshot
from ceibo_core.models.schemas import (
    SingularityCategoryScore,
    SingularityIndex,
    SingularitySnapshotRecord,
    SingularitySignal,
    TrainingRunStatus,
)
from ceibo_core.services.memory import memory_service
from ceibo_core.services.evaluation_harness import evaluation_harness_service
from ceibo_core.services.model_registry import model_registry_service
from ceibo_core.services.training_data import training_data_service
from ceibo_core.services.training_runner import training_runner_service

logger = structlog.get_logger()


class SingularityIndexService:
    def __init__(self) -> None:
        self._fallback_snapshots: deque[SingularitySnapshotRecord] = deque(maxlen=100)

    async def calculate(self) -> SingularityIndex:
        memory_status = await memory_service.status()
        training_stats = await training_data_service.stats()
        latest_runs = training_runner_service.list_runs(limit=5)
        latest_eval = evaluation_harness_service.latest()
        eval_scores = latest_eval.category_scores if latest_eval else {}
        registry_overview = await model_registry_service.overview(None, limit=10)
        project_root = training_data_service.project_root()
        curated_dataset = project_root / "training" / "datasets" / "ceibo_instructions.curated.jsonl"

        categories = [
            self._category(
                "Razonamiento",
                10,
                max(35, eval_scores.get("reasoning", 0)),
                [
                    self._signal("Motor local activo", True, settings.default_llm_provider),
                    self._signal("Modo RAG/reglas", "rag" in settings.ceibo_engine_mode, settings.ceibo_engine_mode),
                    self._signal("Evaluation Harness", bool(latest_eval), self._eval_detail(latest_eval, "reasoning")),
                ],
            ),
            self._category(
                "Memoria",
                10,
                max(
                    self._score_memory(memory_status.vector_enabled, memory_status.local_items),
                    eval_scores.get("rag", 0),
                ),
                [
                    self._signal("Backend de memoria", memory_status.available, memory_status.backend),
                    self._signal(
                        "Memoria vectorial",
                        memory_status.vector_enabled,
                        memory_status.collection_name,
                    ),
                    self._signal("RAG eval", bool(latest_eval), self._eval_detail(latest_eval, "rag")),
                ],
            ),
            self._category(
                "Autonomia",
                10,
                25 if settings.enable_system_control else 15,
                [
                    self._signal(
                        "Control del sistema",
                        settings.enable_system_control,
                        "bloqueado por defecto" if not settings.enable_system_control else "habilitado",
                    ),
                    self._signal("Humano-en-el-bucle", True, "acciones peligrosas requieren control"),
                ],
            ),
            self._category(
                "Uso de herramientas",
                10,
                45,
                [
                    self._signal("API de tareas", True, "task queue local"),
                    self._signal("Sandbox operativo", not settings.enable_system_control, "modo seguro por defecto"),
                ],
            ),
            self._category(
                "Capacidad multiagente",
                10,
                min(100, len(agent_registry) * 10),
                [
                    self._signal("Agentes registrados", len(agent_registry) >= 8, f"{len(agent_registry)} agentes"),
                    self._signal("CORE Orchestrator", True, "routing inicial activo"),
                ],
            ),
            self._category(
                "Entrenamiento propio",
                10,
                self._score_training(
                    training_stats.total_examples,
                    curated_dataset,
                    latest_runs,
                    len(registry_overview.datasets),
                    len(registry_overview.models),
                ),
                [
                    self._signal("Dataset operativo", training_stats.total_examples > 0, f"{training_stats.total_examples} ejemplos"),
                    self._signal("Dataset curado", curated_dataset.exists(), self._count_jsonl(curated_dataset)),
                    self._signal("Runs QLoRA", bool(latest_runs), f"{len(latest_runs)} runs registrados"),
                    self._signal(
                        "Registry",
                        bool(registry_overview.datasets or registry_overview.models),
                        f"{len(registry_overview.datasets)} datasets / {len(registry_overview.models)} modelos",
                    ),
                ],
            ),
            self._category(
                "Autoevaluacion",
                7,
                35 if curated_dataset.exists() else 20,
                [
                    self._signal("Curador de dataset", True, "scoring y deduplicacion"),
                    self._signal("Evaluacion baseline", False, "pendiente eval harness"),
                ],
            ),
            self._category(
                "Seguridad",
                10,
                max(45, eval_scores.get("security", 0)),
                [
                    self._signal("Auditoria base", True, "modelos y servicios preparados"),
                    self._signal("RBAC completo", False, "pendiente implementacion"),
                    self._signal("System control off", not settings.enable_system_control, "seguro por defecto"),
                    self._signal("Security eval", bool(latest_eval), self._eval_detail(latest_eval, "security")),
                ],
            ),
            self._category(
                "Multimodalidad",
                5,
                10,
                [
                    self._signal("Voice Agent definido", True, "STT/TTS en roadmap"),
                    self._signal("Vision/OCR", False, "pendiente"),
                ],
            ),
            self._category(
                "Infraestructura",
                8,
                55,
                [
                    self._signal("Docker Compose", True, "local"),
                    self._signal("Helm/Kubernetes", True, "charts disponibles"),
                    self._signal("Observabilidad", True, "Prometheus/OpenTelemetry ready"),
                ],
            ),
            self._category(
                "Capacidad local",
                5,
                60 if settings.default_llm_provider == "ceibo_local" else 35,
                [
                    self._signal("Provider local-first", settings.default_llm_provider == "ceibo_local", settings.default_llm_provider),
                    self._signal("Ollama-ready", True, settings.ollama_base_url),
                ],
            ),
            self._category(
                "Capacidad distribuida",
                3,
                50 if settings.event_bus_enabled else 25,
                [
                    self._signal("Event bus", settings.event_bus_enabled, settings.nats_url),
                    self._signal("Workers distribuidos", False, "pendiente"),
                ],
            ),
            self._category(
                "Aprendizaje continuo",
                2,
                35 if training_stats.total_examples > 0 else 10,
                [
                    self._signal("Feedback a dataset", training_stats.total_examples > 0, "activo"),
                    self._signal("Promocion de modelos", False, "pendiente model registry"),
                ],
            ),
        ]

        index = round(sum(category.weighted_score for category in categories))
        return SingularityIndex(
            index=max(0, min(100, index)),
            maturity_level=self._maturity_level(index),
            summary="Indice tecnico de progreso hacia inteligencia autonoma progresiva; no representa AGI ni Singularidad alcanzada.",
            categories=categories,
            next_steps=self._next_steps(categories),
        )

    async def capture_snapshot(
        self,
        db: AsyncSession,
        metadata: dict | None = None,
    ) -> SingularitySnapshotRecord:
        current = await self.calculate()
        snapshot = SingularitySnapshotRecord(
            **current.model_dump(),
            snapshot_id=self._snapshot_id(current.updated_at),
            created_at=current.updated_at,
        )
        self._fallback_snapshots.appendleft(snapshot)

        if not settings.persistence_enabled:
            return snapshot

        try:
            record = SingularitySnapshot(
                id=snapshot.snapshot_id,
                index=snapshot.index,
                maturity_level=snapshot.maturity_level,
                summary=snapshot.summary,
                categories=[category.model_dump() for category in snapshot.categories],
                next_steps=snapshot.next_steps,
                snapshot_metadata=metadata or {},
                created_at=snapshot.created_at,
            )
            db.add(record)
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("singularity_snapshot_failed", error=str(exc))
        return snapshot

    async def history(
        self,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[SingularitySnapshotRecord]:
        if not settings.persistence_enabled:
            return list(self._fallback_snapshots)[:limit]

        try:
            result = await db.execute(
                select(SingularitySnapshot)
                .order_by(SingularitySnapshot.created_at.desc())
                .limit(limit)
            )
            records = result.scalars().all()
            return [self._from_record(record) for record in records]
        except SQLAlchemyError as exc:
            logger.warning("singularity_history_failed", error=str(exc))
            return list(self._fallback_snapshots)[:limit]

    def _category(
        self,
        category: str,
        weight: int,
        score: int,
        signals: list[SingularitySignal],
    ) -> SingularityCategoryScore:
        bounded_score = max(0, min(100, score))
        return SingularityCategoryScore(
            category=category,
            weight=weight,
            score=bounded_score,
            weighted_score=round(bounded_score * weight / 100, 2),
            signals=signals,
        )

    def _signal(self, name: str, active: bool, detail: object) -> SingularitySignal:
        return SingularitySignal(name=name, active=active, detail=str(detail))

    def _score_memory(self, vector_enabled: bool, local_items: int) -> int:
        score = 25
        if vector_enabled:
            score += 35
        if local_items:
            score += min(25, local_items)
        return min(100, score)

    def _score_training(
        self,
        total_examples: int,
        curated_dataset: Path,
        latest_runs: list,
        dataset_versions: int = 0,
        model_versions: int = 0,
    ) -> int:
        score = min(35, total_examples * 2)
        if curated_dataset.exists():
            score += 25
        if latest_runs:
            score += 15
        if dataset_versions:
            score += 10
        if model_versions:
            score += 10
        if any(run.status == TrainingRunStatus.COMPLETED for run in latest_runs):
            score += 25
        return min(100, score)

    def _count_jsonl(self, path: Path) -> str:
        if not path.exists():
            return "no disponible"
        total = sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip())
        return f"{total} ejemplos"

    def _maturity_level(self, index: int) -> str:
        if index >= 80:
            return "advanced"
        if index >= 60:
            return "operational"
        if index >= 35:
            return "foundation"
        return "seed"

    def _eval_detail(self, latest_eval, category: str) -> str:
        if not latest_eval:
            return "pendiente"
        score = latest_eval.category_scores.get(category)
        if score is None:
            return "sin casos"
        return f"{score}/100 en {latest_eval.run_id}"

    def _next_steps(self, categories: list[SingularityCategoryScore]) -> list[str]:
        weakest = sorted(categories, key=lambda category: category.score)[:4]
        return [
            f"Mejorar {category.category}: subir score actual {category.score}/100."
            for category in weakest
        ]

    def _snapshot_id(self, updated_at) -> str:
        return f"si-{updated_at.strftime('%Y%m%d-%H%M%S-%f')}"

    def _from_record(self, record: SingularitySnapshot) -> SingularitySnapshotRecord:
        return SingularitySnapshotRecord(
            snapshot_id=record.id,
            index=record.index,
            maturity_level=record.maturity_level,
            summary=record.summary,
            categories=[
                SingularityCategoryScore.model_validate(category)
                for category in record.categories
            ],
            next_steps=list(record.next_steps),
            updated_at=record.created_at,
            created_at=record.created_at,
        )


singularity_index_service = SingularityIndexService()
