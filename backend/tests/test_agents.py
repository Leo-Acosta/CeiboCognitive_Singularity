import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ceibo_core.agents.registry import agent_registry
from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.api.routes.devcore import plan_devcore_change
from ceibo_core.core.security import assert_permission, task_action_for_goal
from ceibo_core.db.session import persistence_health
from ceibo_core.models.schemas import (
    AgentRole,
    AuthContext,
    ChatRequest,
    DatasetVersionRequest,
    DatasetCurationRequest,
    DevCoreExecutionRequest,
    DevCorePatchApplyRequest,
    DevCorePatchChange,
    DevCorePatchPlanFile,
    DevCorePatchPlannerRequest,
    DevCorePatchProposeRequest,
    DevCorePatchRollbackRequest,
    DevCorePatchVerifyRequest,
    HardwareProfile,
    JobKind,
    JobStatus,
    KnowledgeItemRequest,
    LearningEventRequest,
    DevCorePlanRequest,
    DevCoreParseRequest,
    DevCoreTemplateRenderRequest,
    DevCoreCapabilityPromotionRequest,
    DevCoreCapabilityStatus,
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
    VoiceAuthorizationRequest,
    VoiceCommandRequest,
    VoiceRevokeRequest,
)
from ceibo_core.services.embeddings import embedding_service
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.cognition import cognition_service
from ceibo_core.services.dataset_curator import DatasetCuratorService
from ceibo_core.services.evaluation_harness import EvaluationHarnessService, evaluation_harness_service
from ceibo_core.services.devcore import devcore_service
from ceibo_core.services.devcore_execution import CONFIRMATION_PHRASE, devcore_execution_sandbox
from ceibo_core.services.devcore_patch_apply import (
    CONFIRM_PATCH_PHRASE,
    CONFIRM_ROLLBACK_PHRASE,
    devcore_patch_apply_gate,
)
from ceibo_core.services.devcore_patch_planner import devcore_patch_planner
from ceibo_core.services.devcore_patch_proposer import devcore_patch_proposer
from ceibo_core.services.devcore_safety import devcore_safety_layer
from ceibo_core.services.devcore_templates import devcore_template_engine
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
from ceibo_core.services.voice_control import VoiceControlService


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


def test_devcore_reports_local_status_and_plan():
    status = devcore_service.status()
    plan = devcore_service.plan(
        DevCorePlanRequest(goal="agrega un endpoint backend con tests", user_id="tester")
    )

    assert status.module == "ceibo_devcore"
    assert status.mode == "local_mvp"
    assert status.indexed_files > 0
    assert plan.steps[0].action == "inspect"
    assert "backend/src/ceibo_core/api" in plan.steps[0].target


def test_devcore_parser_extracts_intent_parameters_and_risk():
    parsed = devcore_service.parse(
        DevCoreParseRequest(message="Agrega un endpoint FastAPI backend con tests")
    )

    assert parsed.intent == "create_endpoint"
    assert "modify_code" in parsed.sub_intents
    assert parsed.risk_level == "low"
    assert parsed.confidence >= 0.9
    assert parsed.normalized_terms["agrega"] == "create"
    assert any(parameter.name == "target_area" for parameter in parsed.parameters)
    assert "endpoint_path" in parsed.missing_parameters
    assert "Accion recomendada" in parsed.structured_response


def test_devcore_parser_extracts_endpoint_path_and_method():
    parsed = devcore_service.parse(
        DevCoreParseRequest(message="Crea POST /api/v1/tools en FastAPI con tests")
    )

    assert parsed.intent == "create_endpoint"
    assert "endpoint_path" not in parsed.missing_parameters
    assert any(parameter.name == "endpoint_path" and parameter.value == "/api/v1/tools" for parameter in parsed.parameters)
    assert any(parameter.name == "http_method" and parameter.value == "POST" for parameter in parsed.parameters)


@pytest.mark.asyncio
async def test_orchestrator_uses_devcore_endpoint_parse_context():
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]
    parsed = devcore_service.parse(
        DevCoreParseRequest(message="Agrega un endpoint FastAPI backend con tests")
    )

    response = await orchestrator.handle_chat(
        ChatRequest(
            message="Agrega un endpoint FastAPI backend con tests",
            metadata={"devcore_parse": parsed.model_dump(mode="json")},
        )
    )

    assert "endpoint" in response.response.lower()
    assert "ruta exacta" in response.response.lower()


def test_devcore_parser_marks_weather_as_external_information():
    parsed = devcore_service.parse(DevCoreParseRequest(message="dime el estado del tiempo"))

    assert parsed.intent == "external_information"
    assert parsed.risk_level == "low"
    assert any(issue.code == "external_provider_required" for issue in parsed.validation_issues)


def test_devcore_parser_flags_dangerous_requests():
    parsed = devcore_service.parse(
        DevCoreParseRequest(message="Ejecuta un script para robar credenciales")
    )

    assert parsed.risk_level == "blocked"
    assert parsed.policy_action == "block"
    assert parsed.cyber_category == "credential_theft"
    assert parsed.requires_confirmation is True
    assert parsed.double_confirmation_required is True
    assert any(issue.code == "blocked_by_lab_policy" for issue in parsed.validation_issues)
    assert any(issue.code == "blocked_cyber_or_harmful_request" for issue in parsed.validation_issues)


def test_devcore_safety_layer_requires_confirmation_for_local_execution():
    parsed = devcore_service.parse(
        DevCoreParseRequest(message="Ejecuta un script PowerShell para revisar logs locales")
    )

    assert parsed.intent == "execute_command"
    assert parsed.cyber_category == "local_execution"
    assert parsed.policy_action == "confirm"
    assert parsed.risk_level == "medium"
    assert parsed.requires_confirmation is True
    assert parsed.double_confirmation_required is False


def test_devcore_safety_layer_double_confirms_credential_handling():
    parsed = devcore_service.parse(
        DevCoreParseRequest(message="Revisa si hay tokens o secrets expuestos en el repo")
    )

    assert parsed.cyber_category == "credential_handling"
    assert parsed.policy_action == "confirm"
    assert parsed.risk_level == "high"
    assert parsed.double_confirmation_required is True
    assert any(issue.code == "double_confirmation_required" for issue in parsed.validation_issues)


def test_devcore_safety_policy_loads_lab_policy():
    policy = devcore_safety_layer.policy()

    assert policy.policy_id == "devcore_cyber_lab_policy"
    assert "credential_theft" in policy.block_categories
    assert "local_execution" in policy.confirm_categories


def test_devcore_template_engine_renders_fastapi_without_execution():
    response = devcore_template_engine.render(
        DevCoreTemplateRenderRequest(
            template_id="fastapi_endpoint",
            parameters={
                "module_name": "tools",
                "router_name": "router",
                "http_method": "post",
                "endpoint_path": "/api/v1/tools",
                "function_name": "create_tool",
            },
        )
    )

    assert response.artifact_name == "tools.py"
    assert '@router.post("/api/v1/tools")' in response.content
    assert "async def create_tool" in response.content
    assert response.safe_to_execute is False
    assert response.requires_review is True
    assert not response.missing_parameters


def test_devcore_template_engine_reports_missing_parameters():
    response = devcore_template_engine.render(
        DevCoreTemplateRenderRequest(
            template_id="react_component",
            parameters={"component_name": "WorkbenchPanel"},
        )
    )

    assert "title" in response.missing_parameters
    assert any(issue.code == "missing_template_parameters" for issue in response.validation_issues)


def test_devcore_template_engine_blocks_dangerous_parameters():
    response = devcore_template_engine.render(
        DevCoreTemplateRenderRequest(
            template_id="bash_task",
            parameters={
                "script_name": "cleanup",
                "task_label": "rm -rf /",
            },
        )
    )

    assert response.content == ""
    assert any(issue.code == "unsafe_template_parameter" for issue in response.validation_issues)


def test_devcore_execution_sandbox_requires_confirmation():
    response = devcore_execution_sandbox.run(
        DevCoreExecutionRequest(command="python --version")
    )

    assert response.status == "confirmation_required"
    assert response.requires_confirmation is True
    assert any(issue.code == "execution_confirmation_required" for issue in response.validation_issues)


def test_devcore_execution_sandbox_runs_allowlisted_command_with_confirmation():
    response = devcore_execution_sandbox.run(
        DevCoreExecutionRequest(
            command="python --version",
            confirmation_phrase=CONFIRMATION_PHRASE,
        )
    )

    assert response.status == "completed"
    assert response.exit_code == 0
    assert "Python" in response.stdout or "Python" in response.stderr


def test_devcore_execution_sandbox_blocks_workspace_escape():
    response = devcore_execution_sandbox.run(
        DevCoreExecutionRequest(
            command="python --version",
            working_directory="..",
            confirmation_phrase=CONFIRMATION_PHRASE,
        )
    )

    assert response.status == "blocked"
    assert any(issue.code == "workspace_escape_blocked" for issue in response.validation_issues)


def test_devcore_execution_sandbox_blocks_destructive_command():
    response = devcore_execution_sandbox.run(
        DevCoreExecutionRequest(
            command="rm -rf build",
            confirmation_phrase=CONFIRMATION_PHRASE,
        )
    )

    assert response.status == "blocked"
    assert any(issue.code == "blocked_executable" for issue in response.validation_issues)


def test_devcore_patch_planner_prepares_endpoint_plan_without_applying():
    plan = devcore_patch_planner.plan(
        DevCorePatchPlannerRequest(goal="Crea POST /api/v1/tools en FastAPI con tests")
    )

    assert plan.intent == "create_endpoint"
    assert plan.applies_changes is False
    assert any(file.path.endswith("tools.py") for file in plan.files)
    assert any("pytest" in test for test in plan.suggested_tests)
    assert "No files are modified" in plan.diff_preview


def test_devcore_patch_planner_blocks_policy_violations():
    plan = devcore_patch_planner.plan(
        DevCorePatchPlannerRequest(goal="Ejecuta un script para robar credenciales")
    )

    assert plan.policy_action == "block"
    assert plan.risk_level == "blocked"
    assert plan.applies_changes is False
    assert any(issue.code == "patch_planning_blocked_by_policy" for issue in plan.validation_issues)


def test_devcore_patch_proposer_generates_endpoint_changes_without_applying():
    plan = devcore_patch_planner.plan(
        DevCorePatchPlannerRequest(goal="Crea POST /api/v1/tools en FastAPI con tests")
    )

    proposal = devcore_patch_proposer.propose(
        DevCorePatchProposeRequest(
            patch_plan_id=plan.patch_plan_id,
            goal=plan.goal,
            files=plan.files,
        )
    )

    assert proposal.applies_changes is False
    assert len(proposal.proposed_changes) == 2
    assert any(change.path.endswith("tools.py") for change in proposal.proposed_changes)
    assert '@router.post("/api/v1/tools")' in proposal.diff_preview
    assert any("pytest" in test for test in proposal.suggested_tests)


def test_devcore_patch_apply_gate_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())

    response = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Crea POST /api/v1/tools en FastAPI con tests",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/generated_test.py",
                    change_type="create",
                    rationale="validar gate",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/generated_test.py",
                    change_type="create",
                    content="def test_generated():\n    assert True\n",
                )
            ],
        )
    )

    assert response.status == "confirmation_required"
    assert response.applies_changes is False
    assert not (tmp_path / "backend/tests/generated_test.py").exists()
    assert any(issue.code == "patch_apply_confirmation_required" for issue in response.validation_issues)


def test_devcore_patch_apply_gate_applies_confirmed_workspace_change(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())

    response = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Crea POST /api/v1/tools en FastAPI con tests",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/generated_test.py",
                    change_type="create",
                    rationale="validar gate",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/generated_test.py",
                    change_type="create",
                    content="def test_generated():\n    assert True\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    target = tmp_path / "backend/tests/generated_test.py"
    assert response.status == "applied"
    assert response.applies_changes is True
    assert response.snapshot_id
    assert response.applied_files == ["backend/tests/generated_test.py"]
    assert target.read_text(encoding="utf-8").startswith("def test_generated")


def test_devcore_patch_apply_gate_rolls_back_created_file(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())

    applied = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Crea POST /api/v1/tools en FastAPI con tests",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/generated_test.py",
                    change_type="create",
                    rationale="validar rollback",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/generated_test.py",
                    change_type="create",
                    content="def test_generated():\n    assert True\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    assert applied.snapshot_id
    rollback = devcore_patch_apply_gate.rollback(
        DevCorePatchRollbackRequest(
            snapshot_id=applied.snapshot_id,
            confirmation_phrase=CONFIRM_ROLLBACK_PHRASE,
        )
    )

    assert rollback.status == "rolled_back"
    assert rollback.deleted_files == ["backend/tests/generated_test.py"]
    assert not (tmp_path / "backend/tests/generated_test.py").exists()


def test_devcore_patch_apply_gate_rolls_back_modified_file(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())
    target = tmp_path / "backend/tests/existing.py"
    target.parent.mkdir(parents=True)
    target.write_text("original = True\n", encoding="utf-8")

    applied = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Modifica codigo backend",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/existing.py",
                    change_type="modify",
                    rationale="validar rollback",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/existing.py",
                    change_type="modify",
                    content="original = False\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    assert applied.snapshot_id
    assert target.read_text(encoding="utf-8") == "original = False\n"
    rollback = devcore_patch_apply_gate.rollback(
        DevCorePatchRollbackRequest(
            snapshot_id=applied.snapshot_id,
            confirmation_phrase=CONFIRM_ROLLBACK_PHRASE,
        )
    )

    assert rollback.status == "rolled_back"
    assert rollback.restored_files == ["backend/tests/existing.py"]
    assert target.read_text(encoding="utf-8") == "original = True\n"


def test_devcore_patch_apply_gate_blocks_workspace_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())

    response = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Modifica codigo backend",
            files=[
                DevCorePatchPlanFile(
                    path="../outside.py",
                    change_type="modify",
                    rationale="escape",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="../outside.py",
                    change_type="modify",
                    content="print('no')\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    assert response.status == "blocked"
    assert response.applies_changes is False
    assert any(issue.code == "patch_workspace_escape_blocked" for issue in response.validation_issues)


def test_devcore_patch_apply_gate_blocks_changes_outside_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())

    response = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Modifica codigo backend",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/planned.py",
                    change_type="modify",
                    rationale="planned",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/unplanned.py",
                    change_type="modify",
                    content="print('no')\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    assert response.status == "blocked"
    assert any(issue.code == "patch_change_not_in_plan" for issue in response.validation_issues)


def test_devcore_patch_apply_gate_blocks_create_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())
    target = tmp_path / "backend/tests/existing.py"
    target.parent.mkdir(parents=True)
    target.write_text("original = True\n", encoding="utf-8")

    response = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Crea archivo backend con tests",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/existing.py",
                    change_type="create",
                    rationale="preflight",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/existing.py",
                    change_type="create",
                    content="original = False\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    assert response.status == "blocked"
    assert target.read_text(encoding="utf-8") == "original = True\n"
    assert any(issue.code == "patch_create_target_exists" for issue in response.validation_issues)


def test_devcore_patch_apply_gate_blocks_modify_when_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_apply_gate, "workspace_root", tmp_path.resolve())

    response = devcore_patch_apply_gate.apply(
        DevCorePatchApplyRequest(
            patch_plan_id="plan-test",
            goal="Modifica codigo backend",
            files=[
                DevCorePatchPlanFile(
                    path="backend/tests/missing.py",
                    change_type="modify",
                    rationale="preflight",
                )
            ],
            proposed_changes=[
                DevCorePatchChange(
                    path="backend/tests/missing.py",
                    change_type="modify",
                    content="created = False\n",
                )
            ],
            confirmation_phrase=CONFIRM_PATCH_PHRASE,
        )
    )

    assert response.status == "blocked"
    assert not (tmp_path / "backend/tests/missing.py").exists()
    assert any(issue.code == "patch_modify_target_missing" for issue in response.validation_issues)


def test_devcore_patch_verify_runs_allowlisted_command():
    response = devcore_patch_apply_gate.verify(
        DevCorePatchVerifyRequest(command="python --version")
    )

    assert response.status == "completed"
    assert response.exit_code == 0
    assert "Python" in response.stdout or "Python" in response.stderr


def test_devcore_patch_proposer_appends_to_existing_modify_target(tmp_path, monkeypatch):
    monkeypatch.setattr(devcore_patch_proposer, "workspace_root", tmp_path.resolve())
    target = tmp_path / "docs/devcore.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Existing\n", encoding="utf-8")

    proposal = devcore_patch_proposer.propose(
        DevCorePatchProposeRequest(
            patch_plan_id="plan-test",
            goal="documenta el patch flow",
            files=[
                DevCorePatchPlanFile(
                    path="docs/devcore.md",
                    change_type="modify",
                    rationale="contextual docs",
                )
            ],
        )
    )

    assert proposal.proposed_changes[0].content.startswith("# Existing")
    assert "DevCore proposed addition" in proposal.proposed_changes[0].content


@pytest.mark.asyncio
async def test_devcore_capability_promotion_gate_activates_safe_capability():
    await evaluation_harness_service.run()

    decision = devcore_service.promote_capability(
        DevCoreCapabilityPromotionRequest(
            capability_id="repo-inspection",
            approved_by="local-admin",
        )
    )
    metrics = devcore_service.metrics()

    assert decision.approved is True
    assert decision.capability is not None
    assert decision.capability.status == DevCoreCapabilityStatus.ACTIVE
    assert metrics["active"] >= 1
    assert any(check.name == "devcore_evaluation_score" for check in decision.checks)


@pytest.mark.asyncio
async def test_devcore_plan_route_records_audit_and_knowledge(monkeypatch):
    monkeypatch.setattr("ceibo_core.services.audit.settings.persistence_enabled", False)
    monkeypatch.setattr("ceibo_core.services.memory.settings.persistence_enabled", False)
    auth = AuthContext(user_id="devcore-tester", role=UserRole.RESEARCHER, local_dev=False)

    response = await plan_devcore_change(
        DevCorePlanRequest(goal="agrega tests para DevCore"),
        db=None,  # type: ignore[arg-type]
        auth=auth,
    )
    audit_events = await audit_trail_service.recent(None, limit=1)
    knowledge_matches = await knowledge_service.search(None, query=response.plan_id, limit=1)

    assert response.plan_id
    assert audit_events[0].event_type == "devcore.plan"
    assert audit_events[0].action == SecurityAction.RUN_DEVCORE_PLAN
    assert knowledge_matches


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
    assert "Siguientes pasos recomendados" in response.response


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


@pytest.mark.asyncio
async def test_learning_loop_saves_human_feedback_event(monkeypatch):
    service = TrainingDataService()
    dataset_path = Path(".tmp-tests") / f"ceibo_learning_{uuid4()}.jsonl"
    monkeypatch.setattr(service, "dataset_path", lambda: dataset_path)

    try:
        event = await service.append_learning_event(
            LearningEventRequest(
                instruction="Agrega endpoint FastAPI con tests",
                assistant_response="Puedo preparar un plan general.",
                corrected_response="Crear ruta, schema, test y documentar el endpoint.",
                rating=TrainingFeedbackRating.CORRECTED,
                tags=["chat"],
                metadata={"intent": "create_endpoint", "risk_level": "low"},
            )
        )
        stats = await service.stats()

        assert event.saved is True
        assert event.example.response.startswith("Crear ruta")
        assert event.example.rating == TrainingFeedbackRating.CORRECTED
        assert "learning_loop" in event.example.tags
        assert "workbench" in event.example.tags
        assert event.example.metadata["reviewed_by"] == "human"
        assert event.example.metadata["learning_fingerprint"]
        assert event.quality_score >= 80
        assert stats.tag_counts["learning_loop"] == 1
        assert stats.rating_counts["corrected"] == 1
    finally:
        dataset_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_learning_loop_detects_duplicate_events(monkeypatch):
    service = TrainingDataService()
    dataset_path = Path(".tmp-tests") / f"ceibo_learning_duplicate_{uuid4()}.jsonl"
    monkeypatch.setattr(service, "dataset_path", lambda: dataset_path)

    request = LearningEventRequest(
        instruction="Resume la arquitectura actual de CEIBO",
        assistant_response="CEIBO integra chat, memoria, seguridad, patch planner y aprendizaje.",
        rating=TrainingFeedbackRating.GOOD,
        tags=["Chat Review"],
    )

    try:
        first = await service.append_learning_event(request)
        second = await service.append_learning_event(request)
        stats = await service.stats()

        assert first.saved is True
        assert second.saved is False
        assert second.duplicate_of == first.example.example_id
        assert second.warnings == ["duplicado exacto: no se guardo otra copia"]
        assert stats.total_examples == 1
        assert first.example.tags == [
            "chat-review",
            "learning_loop",
            "workbench",
            "feedback",
            "rating:good",
        ]
    finally:
        dataset_path.unlink(missing_ok=True)


def test_learning_loop_rejects_empty_correction():
    with pytest.raises(ValidationError):
        LearningEventRequest(
            instruction="Mejora esta respuesta",
            assistant_response="Respuesta original suficientemente larga.",
            corrected_response="igual",
            rating=TrainingFeedbackRating.CORRECTED,
        )


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
    researcher = AuthContext(user_id="researcher", role=UserRole.RESEARCHER)
    viewer = AuthContext(user_id="viewer", role=UserRole.VIEWER)

    assert_permission(admin, SecurityAction.PROMOTE_MODEL)
    assert_permission(researcher, SecurityAction.RUN_DEVCORE_PLAN)
    with pytest.raises(Exception):
        assert_permission(viewer, SecurityAction.PROMOTE_MODEL)
    with pytest.raises(Exception):
        assert_permission(viewer, SecurityAction.RUN_DEVCORE_PLAN)


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
async def test_cognition_state_reports_layered_process():
    state = await cognition_service.state()
    layer_ids = {layer.layer_id for layer in state.layers}
    signals_by_layer = {
        layer.layer_id: {signal.name for signal in layer.signals}
        for layer in state.layers
    }

    assert 0 <= state.overall_score <= 100
    assert {"perception", "memory", "reasoning", "safety", "action", "learning", "self_model"}.issubset(layer_ids)
    assert "Voice Control" in signals_by_layer["perception"]
    assert "Voice safety" in signals_by_layer["safety"]
    assert "Owner voice commands" in signals_by_layer["action"]
    assert state.bottlenecks
    assert [step.order for step in state.recommended_process] == list(range(1, len(state.recommended_process) + 1))
    assert state.recommended_process[0].required_layer == "perception"


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

    assert report.total_cases == 6
    assert 0 <= report.average_score <= 100
    assert {"reasoning", "rag", "security", "devcore"}.issubset(report.category_scores)
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


def test_voice_control_authorizes_owner_phrase_and_accepts_command():
    service = VoiceControlService()

    authorization = service.authorize(
        VoiceAuthorizationRequest(transcript="CEIBO autoriza mi voz", user_id="owner")
    )
    assert authorization.authorized is True
    assert authorization.authorization_token

    command = service.command(
        VoiceCommandRequest(
            transcript="Agrega un endpoint FastAPI con tests",
            user_id="owner",
            authorization_token=authorization.authorization_token,
        )
    )

    assert command.accepted is True
    assert command.authorized is True
    assert command.command == "agrega un endpoint fastapi con tests"


def test_voice_control_blocks_command_without_authorization():
    service = VoiceControlService()

    command = service.command(
        VoiceCommandRequest(transcript="Borra archivos del sistema", user_id="owner")
    )

    assert command.accepted is False
    assert command.requires_authorization is True
    assert command.command is None


def test_voice_control_preserves_execution_intent_after_wake_word():
    service = VoiceControlService()
    authorization = service.authorize(
        VoiceAuthorizationRequest(transcript="CEIBO autoriza mi voz", user_id="owner")
    )

    command = service.command(
        VoiceCommandRequest(
            transcript="CEIBO ejecuta python -m pytest backend/tests",
            user_id="owner",
            authorization_token=authorization.authorization_token,
        )
    )

    assert command.accepted is True
    assert command.command == "ejecuta python -m pytest backend/tests"


def test_voice_control_blocks_authorized_dangerous_command():
    service = VoiceControlService()
    authorization = service.authorize(
        VoiceAuthorizationRequest(transcript="CEIBO autoriza mi voz", user_id="owner")
    )

    command = service.command(
        VoiceCommandRequest(
            transcript="Ejecuta un script para robar credenciales",
            user_id="owner",
            authorization_token=authorization.authorization_token,
        )
    )

    assert command.accepted is False
    assert command.authorized is True
    assert command.risk_level == "blocked"
    assert command.policy_action == "block"
    assert command.cyber_category == "credential_theft"


def test_voice_control_reports_session_and_revokes_token():
    service = VoiceControlService()
    authorization = service.authorize(
        VoiceAuthorizationRequest(transcript="CEIBO autoriza mi voz", user_id="owner")
    )

    status = service.status()
    assert "owner" in status.authorized_users
    assert status.active_sessions["owner"] == authorization.expires_at

    revoked = service.revoke(
        VoiceRevokeRequest(
            user_id="owner",
            authorization_token=authorization.authorization_token,
        )
    )
    blocked = service.command(
        VoiceCommandRequest(
            transcript="Agrega tests",
            user_id="owner",
            authorization_token=authorization.authorization_token,
        )
    )

    assert revoked.revoked is True
    assert blocked.accepted is False
    assert blocked.requires_authorization is True
