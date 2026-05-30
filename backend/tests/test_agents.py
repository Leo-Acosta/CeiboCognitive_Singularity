import json
from pathlib import Path
from uuid import uuid4

import pytest

from ceibo_core.agents.registry import agent_registry
from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.models.schemas import (
    AgentRole,
    ChatRequest,
    DatasetCurationRequest,
    HardwareProfile,
    ModelRecommendationRequest,
    TaskRequest,
    TeacherReviewRequest,
    TeacherSyntheticRequest,
    QloraTrainingRequest,
    TrainingExample,
    TrainingFeedbackRating,
    TrainingFeedbackRequest,
    TrainingPlanRequest,
)
from ceibo_core.services.embeddings import embedding_service
from ceibo_core.services.dataset_curator import DatasetCuratorService
from ceibo_core.services.memory import memory_service
from ceibo_core.services.model_catalog import model_catalog_service
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
