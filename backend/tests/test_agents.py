import json
from pathlib import Path
from uuid import uuid4

import pytest

from ceibo_core.agents.registry import agent_registry
from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.core.security import assert_permission, task_action_for_goal
from ceibo_core.db.session import persistence_health
from ceibo_core.models.schemas import (
    AgentRole,
    AuthContext,
    ChatRequest,
    DatasetVersionRequest,
    DatasetCurationRequest,
    HardwareProfile,
    JobKind,
    JobStatus,
    KnowledgeItemRequest,
    LongRunningJobRequest,
    ModelRecommendationRequest,
    ModelPromotionRequest,
    ModelVersionRequest,
    ModelVersionStatus,
    SecurityAction,
    TaskRequest,
    TeacherReviewRequest,
    TeacherSyntheticRequest,
    QloraTrainingRequest,
    TrainingExample,
    TrainingFeedbackRating,
    TrainingFeedbackRequest,
    TrainingPlanRequest,
    UserRole,
)
from ceibo_core.services.embeddings import embedding_service
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.dataset_curator import DatasetCuratorService
from ceibo_core.services.evaluation_harness import EvaluationHarnessService
from ceibo_core.services.jobs import long_running_job_service
from ceibo_core.services.memory import knowledge_service, memory_service
from ceibo_core.services.model_catalog import model_catalog_service
from ceibo_core.services.model_registry import ModelRegistryService
from ceibo_core.services.orchestration import orchestration_service
from ceibo_core.services.singularity_index import SingularityIndexService
from ceibo_core.services.tasks import task_store
from ceibo_core.services.teacher_agent import TeacherAgentService
from ceibo_core.services.training_data import TrainingDataService
from ceibo_core.services.training_runner import TrainingRunnerService


@pytest.mark.asyncio
async def test_orchestrator_routes_kubernetes_task_to_infrastructure_agent():
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]

    response = await orchestrator.handle_task(TaskRequest(goal="revisar logs de kubernetes"))

    assert response.assigned_agent == AgentRole.INFRASTRUCTURE


@pytest.mark.asyncio
async def test_orchestrator_returns_orchestration_trace_for_task():
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]

    response = await orchestrator.handle_task(
        TaskRequest(goal="aplica hardening de seguridad y revisa auditoria", user_id="tester")
    )

    assert response.assigned_agent == AgentRole.CYBERSECURITY
    assert response.orchestration_trace is not None
    assert response.orchestration_trace.primary_agent == AgentRole.CYBERSECURITY
    assert response.orchestration_trace.steps[0].agent == AgentRole.CORE_ORCHESTRATOR
    assert any(step.status == "completed" for step in response.orchestration_trace.steps)


def test_orchestration_plan_adds_support_handoffs():
    trace = orchestration_service.plan(
        TaskRequest(goal="automatiza un workflow docker con memoria rag", user_id="tester")
    )

    assert trace.primary_agent in {AgentRole.AUTOMATION, AgentRole.INFRASTRUCTURE}
    assert len(trace.steps) >= 3
    assert any(step.action == "support" for step in trace.steps)


@pytest.mark.asyncio
async def test_orchestrator_returns_session_and_memory_context():
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]

    response = await orchestrator.handle_chat(
        ChatRequest(
            message="continua la conversacion",
            session_id="session-test",
            metadata={"memory_context": ["user: recuerda que usamos Qdrant"]},
        )
    )

    assert response.session_id == "session-test"
    assert response.memory_context == ["user: recuerda que usamos Qdrant"]


@pytest.mark.asyncio
async def test_task_store_keeps_local_recent_tasks_when_persistence_is_disabled():
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]
    request = TaskRequest(goal="automatiza un workflow con playwright", user_id="local-user")
    response = await orchestrator.handle_task(request)

    await task_store.append_task(None, request, response)  # type: ignore[arg-type]
    tasks = await task_store.recent_tasks(None, limit=1)  # type: ignore[arg-type]

    assert tasks[0].goal == request.goal
    assert tasks[0].assigned_agent == AgentRole.AUTOMATION


@pytest.mark.asyncio
async def test_long_running_job_runs_to_completion(monkeypatch):
    monkeypatch.setattr("ceibo_core.services.jobs.settings.persistence_enabled", False)

    record = await long_running_job_service.enqueue(
        None,
        LongRunningJobRequest(
            kind=JobKind.TASK,
            title="procesar auditoria larga",
            user_id="tester",
            metadata={"source": "test"},
        ),
    )
    completed = await long_running_job_service.run(None, record.job_id)
    recent = await long_running_job_service.recent(None, limit=1)

    assert completed.status == JobStatus.COMPLETED
    assert completed.progress == 100
    assert completed.result["kind"] == "task"
    assert recent[0].job_id == record.job_id


@pytest.mark.asyncio
async def test_long_running_job_reports_missing_job(monkeypatch):
    monkeypatch.setattr("ceibo_core.services.jobs.settings.persistence_enabled", False)

    with pytest.raises(ValueError):
        await long_running_job_service.run(None, "missing-job")


@pytest.mark.asyncio
async def test_local_embeddings_are_deterministic():
    first = await embedding_service.embed("ceibo core memoria vectorial")
    second = await embedding_service.embed("ceibo core memoria vectorial")

    assert first == second
    assert len(first) > 0


@pytest.mark.asyncio
async def test_memory_service_retrieves_relevant_local_memory():
    session_id = "test-rag-memory"
    await memory_service.remember(
        session_id=session_id,
        text="Qdrant almacena memoria vectorial para CEIBO CORE",
        metadata={"kind": "test"},
    )

    matches = await memory_service.retrieve(session_id=session_id, query="memoria vectorial", limit=1)

    assert matches
    assert "Qdrant" in matches[0].content


@pytest.mark.asyncio
async def test_memory_service_redacts_sensitive_values():
    record = await memory_service.remember(
        session_id="test-memory-safety",
        text="api_key=sk-testsecretvalue123456789 para pruebas",
        metadata={"kind": "secret-test"},
    )

    assert "sk-testsecretvalue" not in record.content
    assert "[REDACTED_SECRET]" in record.content
    assert record.metadata["redacted"] is True


@pytest.mark.asyncio
async def test_knowledge_service_adds_searchable_sanitized_item(monkeypatch):
    monkeypatch.setattr("ceibo_core.services.memory.settings.persistence_enabled", False)

    item = await knowledge_service.add(
        None,
        KnowledgeItemRequest(
            title="Arquitectura Sprint 9",
            content="La memoria progresiva usa token=supersecretvalue para validar redaccion.",
            source="test",
            tags=["arquitectura", "memoria"],
        ),
    )
    matches = await knowledge_service.search(None, query="progresiva", limit=3)
    status = await knowledge_service.status(None)

    assert item.item_id
    assert "supersecretvalue" not in item.content
    assert item.metadata["redacted"] is True
    assert any(match.item_id == item.item_id for match in matches)
    assert status.total_items >= 1
    assert "credential-redaction" in status.safety_filters


@pytest.mark.asyncio
async def test_ceibo_engine_is_local_first_and_detects_training_intent():
    status = ceibo_engine.status()
    response = await ceibo_engine.generate(
        system_prompt="",
        user_message="quiero entrenar mi propia IA local con dataset",
    )

    assert status.provider == "ceibo_local"
    assert status.local_first is True
    assert "Ayudar" in status.core_directive
    assert "training" in response.intents
    assert "dataset" in response.response.lower()
    assert "Directiva" in response.response


def test_model_catalog_recommends_local_model_for_available_vram():
    model = model_catalog_service.recommend(
        ModelRecommendationRequest(
            use_case="coding automation devops",
            hardware=HardwareProfile(gpu_vram_gb=16, system_ram_gb=32, has_cuda=True),
        )
    )

    assert model.model_id
    assert "qlora" in model.training_methods
    assert model.min_vram_gb <= 16


def test_training_plan_can_prepare_from_scratch_research_path():
    plan = model_catalog_service.build_training_plan(
        TrainingPlanRequest(
            use_case="from_scratch",
            hardware=HardwareProfile(gpu_vram_gb=8, system_ram_gb=32, has_cuda=True),
            train_from_scratch=True,
        )
    )

    assert plan.strategy == "pretraining_from_scratch"
    assert plan.selected_model.model_id == "tiny-ceibo-scratch"
    assert plan.warnings


def test_training_example_accepts_legacy_dataset_records():
    example = TrainingExample.model_validate(
        {
            "instruction": "Explica CEIBO CORE",
            "response": "CEIBO CORE es un asistente local multiagente.",
        }
    )

    assert example.example_id
    assert example.source == "manual"
    assert example.rating is None


@pytest.mark.asyncio
async def test_training_data_service_collects_feedback_and_stats(monkeypatch):
    service = TrainingDataService()
    dataset_path = Path(".tmp-tests") / f"ceibo_dataset_{uuid4()}.jsonl"
    monkeypatch.setattr(service, "dataset_path", lambda: dataset_path)

    try:
        example = await service.append_feedback(
            TrainingFeedbackRequest(
                instruction="Como entreno a CEIBO?",
                original_response="Usa un dataset.",
                corrected_response="Crea ejemplos, valida el JSONL y luego ejecuta QLoRA local.",
                rating=TrainingFeedbackRating.CORRECTED,
                tags=["training"],
            )
        )
        examples = await service.list_examples()
        stats = await service.stats()

        assert example.response.startswith("Crea ejemplos")
        assert examples[0].rating == TrainingFeedbackRating.CORRECTED
        assert stats.total_examples == 1
        assert stats.tag_counts["training"] == 1
        assert stats.rating_counts["corrected"] == 1
        assert stats.source_counts["dashboard"] == 1
    finally:
        dataset_path.unlink(missing_ok=True)


def test_dataset_curator_scores_deduplicates_and_exports_jsonl():
    service = DatasetCuratorService()
    test_dir = Path(".tmp-tests")
    test_dir.mkdir(exist_ok=True)
    source_path = test_dir / f"curation_source_{uuid4()}.jsonl"
    output_path = test_dir / f"curation_output_{uuid4()}.jsonl"

    records = [
        {
            "instruction": "Explica como preparar un dataset para CEIBO CORE",
            "response": "Crea ejemplos claros, valida el JSONL y exporta datos curados.",
            "tags": ["training", "training"],
            "rating": "good",
            "source": "dashboard",
        },
        {
            "instruction": "Explica como preparar un dataset para CEIBO CORE",
            "response": "Crea ejemplos claros, valida el JSONL y exporta datos curados.",
            "tags": ["training"],
            "rating": "good",
            "source": "dashboard",
        },
        {
            "instruction": "IA",
            "response": "ok",
            "rating": "bad",
        },
    ]
    try:
        source_path.write_text(
            "\n".join([*map(json.dumps, records), "{bad json"]),
            encoding="utf-8",
        )

        report = service.curate(
            DatasetCurationRequest(
                source_path=str(source_path.resolve().relative_to(service.project_root())),
                output_path=str(output_path.resolve().relative_to(service.project_root())),
                min_score=60,
            ),
            write_output=True,
        )

        assert report.parsed_examples == 3
        assert report.invalid_lines == 1
        assert report.duplicate_examples == 1
        assert report.kept_examples == 1
        assert report.output_path == str(output_path.resolve())
        assert output_path.exists()
        assert len(output_path.read_text(encoding="utf-8").splitlines()) == 1
        assert report.preview_examples[0].quality_score >= 60
    finally:
        source_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def test_training_runner_builds_qlora_preflight_command():
    service = TrainingRunnerService()
    command = service._build_command(
        QloraTrainingRequest(
            config_path="training/configs/ceibo_qlora.local.json",
            max_steps=1,
            local_files_only=True,
        ),
        run_id="qlora-test",
        preflight_only=True,
    )

    assert "run_qlora.py" in command[1]
    assert "--preflight-only" in command
    assert "--local-files-only" in command
    assert "--max-steps" in command


def test_training_runner_prefers_local_qlora_venv(monkeypatch):
    service = TrainingRunnerService()
    monkeypatch.setattr(
        service,
        "project_root",
        lambda: Path("C:/project").resolve(),
    )
    monkeypatch.setattr(Path, "exists", lambda self: str(self).endswith("python.exe"))

    assert service.runner_python().endswith(".venv-qlora\\Scripts\\python.exe")


def test_rbac_allows_admin_and_blocks_viewer_sensitive_action():
    admin = AuthContext(user_id="admin", role=UserRole.ADMIN)
    viewer = AuthContext(user_id="viewer", role=UserRole.VIEWER)

    assert_permission(admin, SecurityAction.PROMOTE_MODEL)
    with pytest.raises(Exception):
        assert_permission(viewer, SecurityAction.PROMOTE_MODEL)


def test_task_policy_classifies_infrastructure_and_system_goals():
    assert task_action_for_goal("revisar logs de kubernetes") == SecurityAction.RUN_INFRA_TASK
    assert task_action_for_goal("abrir terminal y tocar archivos") == SecurityAction.RUN_SYSTEM_TASK
    assert task_action_for_goal("resume el estado") == SecurityAction.CREATE_TASK


@pytest.mark.asyncio
async def test_audit_trail_records_local_sensitive_action(monkeypatch):
    monkeypatch.setattr("ceibo_core.services.audit.settings.persistence_enabled", False)
    auth = AuthContext(user_id="admin", role=UserRole.ADMIN)

    event = await audit_trail_service.record(
        None,
        auth=auth,
        event_type="test.sensitive_action",
        actor="test",
        action=SecurityAction.PROMOTE_MODEL,
        allowed=True,
        payload={"target": "model-1"},
    )
    recent = await audit_trail_service.recent(None, limit=1)

    assert recent[0].event_id == event.event_id
    assert recent[0].role == UserRole.ADMIN
    assert recent[0].action == SecurityAction.PROMOTE_MODEL
    assert recent[0].payload["target"] == "model-1"


@pytest.mark.asyncio
async def test_singularity_index_returns_weighted_progress():
    report = await SingularityIndexService().calculate()

    assert 0 <= report.index <= 100
    assert report.maturity_level in {"seed", "foundation", "operational", "advanced"}
    assert sum(category.weight for category in report.categories) == 100
    assert any(category.category == "Entrenamiento propio" for category in report.categories)
    assert report.next_steps


@pytest.mark.asyncio
async def test_singularity_index_captures_local_history(monkeypatch):
    service = SingularityIndexService()
    monkeypatch.setattr("ceibo_core.services.singularity_index.settings.persistence_enabled", False)

    snapshot = await service.capture_snapshot(None)  # type: ignore[arg-type]
    history = await service.history(None, limit=5)  # type: ignore[arg-type]

    assert history
    assert history[0].snapshot_id == snapshot.snapshot_id
    assert history[0].index == snapshot.index


@pytest.mark.asyncio
async def test_evaluation_harness_runs_core_suites():
    report = await EvaluationHarnessService().run()

    assert report.total_cases == 5
    assert 0 <= report.average_score <= 100
    assert {"reasoning", "rag", "security"}.issubset(report.category_scores)
    assert report.results[0].expected_signals
    assert report.status in {"passed", "needs_attention"}


@pytest.mark.asyncio
async def test_model_registry_registers_dataset_and_active_model(monkeypatch):
    service = ModelRegistryService()
    monkeypatch.setattr("ceibo_core.services.model_registry.settings.persistence_enabled", False)

    dataset = await service.register_dataset(
        None,
        DatasetVersionRequest(
            name="seed",
            path="training/datasets/ceibo_seed.jsonl",
            source="test",
        ),
    )
    model = await service.register_model(
        None,
        ModelVersionRequest(
            name="ceibo-test",
            base_model="ceibo_local",
            dataset_version_id=dataset.version_id,
            status=ModelVersionStatus.ACTIVE,
        ),
    )
    overview = await service.overview(None)

    assert dataset.examples > 0
    assert len(dataset.sha256) == 64
    assert model.status == ModelVersionStatus.ACTIVE
    assert overview.active_model is not None
    assert overview.active_model.name == "ceibo-test"


@pytest.mark.asyncio
async def test_model_registry_is_idempotent_for_same_dataset_and_model(monkeypatch):
    service = ModelRegistryService()
    monkeypatch.setattr("ceibo_core.services.model_registry.settings.persistence_enabled", False)

    first_dataset = await service.register_dataset(
        None,
        DatasetVersionRequest(
            name="seed",
            path="training/datasets/ceibo_seed.jsonl",
            source="test",
        ),
    )
    second_dataset = await service.register_dataset(
        None,
        DatasetVersionRequest(
            name="seed-copy",
            path="training/datasets/ceibo_seed.jsonl",
            source="test",
        ),
    )
    first_model = await service.register_model(
        None,
        ModelVersionRequest(
            name="ceibo-test",
            base_model="ceibo_local",
            dataset_version_id=first_dataset.version_id,
        ),
    )
    second_model = await service.register_model(
        None,
        ModelVersionRequest(
            name="ceibo-test",
            base_model="ceibo_local",
            dataset_version_id=first_dataset.version_id,
        ),
    )
    overview = await service.overview(None)

    assert first_dataset.version_id == second_dataset.version_id
    assert first_model.version_id == second_model.version_id
    assert len(overview.datasets) == 1
    assert len(overview.models) == 1


@pytest.mark.asyncio
async def test_persistence_health_reports_disabled_state(monkeypatch):
    monkeypatch.setattr("ceibo_core.db.session.settings.persistence_enabled", False)

    health = await persistence_health()

    assert health.enabled is False
    assert health.available is False
    assert health.error == "persistence disabled"
    assert "***:***@" in health.database_url_safe


@pytest.mark.asyncio
async def test_model_promotion_gate_blocks_without_human_approval(monkeypatch):
    service = ModelRegistryService()
    monkeypatch.setattr("ceibo_core.services.model_registry.settings.persistence_enabled", False)
    dataset = await service.register_dataset(
        None,
        DatasetVersionRequest(
            name="seed",
            path="training/datasets/ceibo_seed.jsonl",
            source="test",
        ),
    )
    model = await service.register_model(
        None,
        ModelVersionRequest(
            name="candidate",
            base_model="ceibo_local",
            dataset_version_id=dataset.version_id,
        ),
    )

    decision = await service.promote_model(
        None,
        ModelPromotionRequest(
            model_version_id=model.version_id,
            require_evaluation=False,
        ),
    )

    assert decision.approved is False
    assert any(check.name == "human_approval" and not check.passed for check in decision.checks)


@pytest.mark.asyncio
async def test_model_promotion_gate_activates_approved_candidate(monkeypatch):
    service = ModelRegistryService()
    monkeypatch.setattr("ceibo_core.services.model_registry.settings.persistence_enabled", False)
    dataset = await service.register_dataset(
        None,
        DatasetVersionRequest(
            name="seed",
            path="training/datasets/ceibo_seed.jsonl",
            source="test",
        ),
    )
    original = await service.register_model(
        None,
        ModelVersionRequest(
            name="original",
            base_model="ceibo_local",
            status=ModelVersionStatus.ACTIVE,
        ),
    )
    candidate = await service.register_model(
        None,
        ModelVersionRequest(
            name="candidate",
            base_model="ceibo_local",
            dataset_version_id=dataset.version_id,
        ),
    )

    decision = await service.promote_model(
        None,
        ModelPromotionRequest(
            model_version_id=candidate.version_id,
            approved_by="local-admin",
            require_evaluation=False,
        ),
    )
    overview = await service.overview(None)
    models = {model.version_id: model for model in overview.models}

    assert decision.approved is True
    assert decision.promoted_model is not None
    assert overview.active_model is not None
    assert overview.active_model.version_id == candidate.version_id
    assert models[original.version_id].status == ModelVersionStatus.APPROVED


@pytest.mark.asyncio
async def test_teacher_agent_reviews_ceibo_response_with_structured_feedback(monkeypatch):
    service = TeacherAgentService()

    async def fake_generate(prompt: str) -> str:
        assert "Directiva maestra" in prompt
        return json.dumps(
            {
                "score": 0.88,
                "passed": True,
                "issues": ["Agregar comando concreto"],
                "strengths": ["Explica con claridad"],
                "ideal_response": "Primero cura el dataset y luego ejecuta QLoRA.",
            }
        )

    monkeypatch.setattr(service, "_ollama_generate", fake_generate)
    review = await service.review_response(
        TeacherReviewRequest(
            prompt="Como entreno CEIBO?",
            ceibo_response="Usa datos.",
            expected_traits=["pasos claros"],
            category="training",
        )
    )

    assert review.score == 88
    assert review.passed is True
    assert review.ideal_response.startswith("Primero cura")


@pytest.mark.asyncio
async def test_teacher_agent_generates_synthetic_training_examples(monkeypatch):
    service = TeacherAgentService()

    async def fake_generate(prompt: str) -> str:
        assert "Genera datos de entrenamiento" in prompt
        return json.dumps(
            {
                "examples": [
                    {
                        "instruction": "Explica el curador de dataset",
                        "input": "",
                        "response": "El curador valida, puntua y exporta JSONL entrenable.",
                        "tags": ["training"],
                    }
                ]
            }
        )

    monkeypatch.setattr(service, "_ollama_generate", fake_generate)
    result = await service.generate_synthetic_examples(
        TeacherSyntheticRequest(topic="dataset trainer", count=1, tags=["ceibo"])
    )

    assert len(result.examples) == 1
    assert result.examples[0].source == "ollama-mistral-teacher"
    assert "teacher:mistral" in result.examples[0].tags


@pytest.mark.asyncio
async def test_teacher_agent_recovers_score_from_jsonish_model_output(monkeypatch):
    service = TeacherAgentService()

    async def fake_generate(prompt: str) -> str:
        return """
{
  "score": 0.7,
  "passed": false,
  "issues": ["Falta detalle"],
  "strengths": ["Menciona dataset"],
  "ideal_response": "Paso uno
Paso dos"
}
"""

    monkeypatch.setattr(service, "_ollama_generate", fake_generate)
    review = await service.review_response(
        TeacherReviewRequest(prompt="Entrena CEIBO", ceibo_response="Usa dataset.")
    )

    assert review.score == 70
    assert review.issues == ["Falta detalle"]
    assert "Paso uno" in review.ideal_response
