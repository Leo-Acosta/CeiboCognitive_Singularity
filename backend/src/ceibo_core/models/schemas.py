from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentRole(StrEnum):
    CORE_ORCHESTRATOR = "core_orchestrator"
    INFRASTRUCTURE = "infrastructure"
    CYBERSECURITY = "cybersecurity"
    RESEARCH = "research"
    AUTOMATION = "automation"
    MEMORY = "memory"
    VOICE = "voice"
    SYSTEM_CONTROL = "system_control"


class TaskStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(StrEnum):
    GENERIC = "generic"
    TASK = "task"
    EVALUATION = "evaluation"
    TRAINING = "training"


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class SecurityAction(StrEnum):
    READ_STATUS = "read_status"
    RUN_EVALUATION = "run_evaluation"
    MANAGE_REGISTRY = "manage_registry"
    PROMOTE_MODEL = "promote_model"
    START_TRAINING = "start_training"
    CREATE_TASK = "create_task"
    RUN_INFRA_TASK = "run_infra_task"
    RUN_SYSTEM_TASK = "run_system_task"


class AuthContext(BaseModel):
    user_id: str
    role: UserRole
    local_dev: bool = False


class SecurityPolicyStatus(BaseModel):
    rbac_enforced: bool
    local_dev_admin_enabled: bool
    effective_user: AuthContext
    role_permissions: dict[str, list[str]]


class AuditEventRecord(BaseModel):
    event_id: str
    user_id: str
    role: UserRole | None = None
    event_type: str
    actor: str
    action: SecurityAction | None = None
    allowed: bool | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PersistenceHealth(BaseModel):
    enabled: bool
    available: bool
    database_url_safe: str
    tables: list[str] = Field(default_factory=list)
    error: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    user_id: str = "local-user"
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str
    agent: AgentRole
    session_id: str | None = None
    memory_context: list[str] = Field(default_factory=list)
    trace_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    requested_agent: AgentRole | None = None
    user_id: str = "local-user"
    priority: int = Field(default=5, ge=1, le=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    status: TaskStatus = TaskStatus.ACCEPTED
    assigned_agent: AgentRole
    summary: str
    orchestration_trace: "OrchestrationTraceRecord | None" = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskRecord(BaseModel):
    task_id: str
    goal: str
    status: TaskStatus
    assigned_agent: AgentRole
    priority: int
    created_at: datetime


class AgentDescriptor(BaseModel):
    role: AgentRole
    name: str
    description: str
    capabilities: list[str]
    enabled: bool = True


class OrchestrationStep(BaseModel):
    agent: AgentRole
    action: str
    reason: str
    status: str = "planned"


class OrchestrationTraceRecord(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str | None = None
    user_id: str = "local-user"
    goal: str
    primary_agent: AgentRole
    route_reason: str
    steps: list[OrchestrationStep]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LongRunningJobRequest(BaseModel):
    kind: JobKind = JobKind.GENERIC
    title: str = Field(min_length=1, max_length=240)
    user_id: str = "local-user"
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LongRunningJobRecord(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: JobKind
    title: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    current_step: str = "queued"
    user_id: str = "local-user"
    task_id: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCoreStatus(BaseModel):
    module: str = "ceibo_devcore"
    mode: str = "local_mvp"
    capabilities: list[str]
    repo_root: str
    indexed_files: int
    writable: bool = False


class DevCorePlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    user_id: str = "local-user"
    context: list[str] = Field(default_factory=list)


class DevCorePlanStep(BaseModel):
    order: int
    action: str
    target: str
    safety: str


class DevCorePlanResponse(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    summary: str
    recommended_agent: AgentRole = AgentRole.AUTOMATION
    steps: list[DevCorePlanStep]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryRememberRequest(BaseModel):
    session_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    user_id: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRecord(BaseModel):
    memory_id: str
    session_id: str
    content: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemorySearchResponse(BaseModel):
    session_id: str
    query: str
    matches: list[MemoryRecord]


class KnowledgeItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1)
    source: str = "manual"
    user_id: str = "local-user"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeItemRecord(BaseModel):
    item_id: str
    title: str
    content: str
    source: str
    user_id: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeSearchResponse(BaseModel):
    query: str
    matches: list[KnowledgeItemRecord]


class KnowledgeStatus(BaseModel):
    backend: str
    total_items: int
    sanitized_items: int
    safety_filters: list[str]


class MemoryHealth(BaseModel):
    backend: str
    available: bool
    vector_enabled: bool
    embedding_provider: str
    collection_name: str
    local_items: int


class EngineGenerateRequest(BaseModel):
    message: str = Field(min_length=1)
    system_prompt: str = ""
    context: list[str] = Field(default_factory=list)
    user_id: str = "local-user"


class EngineGenerateResponse(BaseModel):
    response: str
    model_id: str
    mode: str
    intents: list[str] = Field(default_factory=list)
    used_context: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EngineStatus(BaseModel):
    model_id: str
    mode: str
    provider: str
    trainable: bool
    local_first: bool
    dataset_path: str
    core_directive: str


class TrainingFeedbackRating(StrEnum):
    GOOD = "good"
    BAD = "bad"
    CORRECTED = "corrected"


class TrainingExampleRequest(BaseModel):
    instruction: str = Field(min_length=1)
    response: str = Field(min_length=1)
    input: str = ""
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingExample(BaseModel):
    example_id: str = Field(default_factory=lambda: str(uuid4()))
    instruction: str
    input: str = ""
    response: str
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    rating: TrainingFeedbackRating | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrainingFeedbackRequest(BaseModel):
    instruction: str = Field(min_length=1)
    original_response: str = Field(min_length=1)
    input: str = ""
    corrected_response: str | None = None
    rating: TrainingFeedbackRating = TrainingFeedbackRating.GOOD
    tags: list[str] = Field(default_factory=list)
    source: str = "dashboard"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingDatasetStats(BaseModel):
    dataset_path: str
    total_examples: int
    tag_counts: dict[str, int] = Field(default_factory=dict)
    rating_counts: dict[str, int] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(default_factory=dict)
    last_updated: datetime | None = None


class DatasetIssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DatasetCurationRequest(BaseModel):
    source_path: str | None = None
    output_path: str | None = None
    min_score: int = Field(default=60, ge=0, le=100)
    min_instruction_chars: int = Field(default=8, ge=1)
    min_response_chars: int = Field(default=24, ge=1)
    include_bad_rated: bool = False
    max_examples: int | None = Field(default=None, ge=1)


class DatasetCurationIssue(BaseModel):
    line_number: int | None = None
    example_id: str | None = None
    severity: DatasetIssueSeverity
    code: str
    message: str


class CuratedTrainingExample(TrainingExample):
    quality_score: int = Field(ge=0, le=100)
    quality_notes: list[str] = Field(default_factory=list)


class DatasetCurationReport(BaseModel):
    source_path: str
    output_path: str | None = None
    total_lines: int
    parsed_examples: int
    kept_examples: int
    dropped_examples: int
    invalid_lines: int
    duplicate_examples: int
    average_score: float
    score_buckets: dict[str, int] = Field(default_factory=dict)
    issues: list[DatasetCurationIssue] = Field(default_factory=list)
    preview_examples: list[CuratedTrainingExample] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TeacherStatus(BaseModel):
    provider: str
    base_url: str
    model: str
    available: bool
    installed_models: list[str] = Field(default_factory=list)
    error: str | None = None


class TeacherReviewRequest(BaseModel):
    prompt: str = Field(min_length=1)
    ceibo_response: str = Field(min_length=1)
    expected_traits: list[str] = Field(default_factory=list)
    category: str = "general"
    save_to_dataset: bool = False


class TeacherReviewResponse(BaseModel):
    prompt: str
    ceibo_response: str
    teacher_model: str
    score: int = Field(ge=0, le=100)
    passed: bool
    issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    ideal_response: str
    raw_feedback: str = ""
    saved_example: TrainingExample | None = None


class TeacherSyntheticRequest(BaseModel):
    topic: str = Field(min_length=1)
    count: int = Field(default=3, ge=1, le=8)
    difficulty: str = "intermediate"
    tags: list[str] = Field(default_factory=list)
    save_to_dataset: bool = False


class TeacherSyntheticResponse(BaseModel):
    teacher_model: str
    examples: list[TrainingExample] = Field(default_factory=list)
    saved_count: int = 0
    raw_output: str = ""


class EvaluationCaseResult(BaseModel):
    case_id: str
    category: str
    prompt: str
    passed: bool
    score: int = Field(ge=0, le=100)
    expected_signals: list[str] = Field(default_factory=list)
    observed_signals: list[str] = Field(default_factory=list)
    response_preview: str = ""
    notes: list[str] = Field(default_factory=list)


class EvaluationSuiteReport(BaseModel):
    run_id: str
    status: str
    total_cases: int
    passed_cases: int
    average_score: int = Field(ge=0, le=100)
    category_scores: dict[str, int] = Field(default_factory=dict)
    results: list[EvaluationCaseResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrainingRunStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class QloraTrainingRequest(BaseModel):
    config_path: str = "training/configs/ceibo_qlora.local.json"
    dataset_path: str | None = None
    output_dir: str | None = None
    base_model: str | None = None
    max_steps: int | None = Field(default=1, ge=1)
    local_files_only: bool | None = None


class TrainingRunnerDependency(BaseModel):
    name: str
    available: bool
    version: str | None = None
    required: bool = True
    note: str | None = None


class TrainingRunnerReport(BaseModel):
    run_id: str
    status: TrainingRunStatus
    config_path: str
    dataset_path: str
    output_dir: str
    base_model: str
    command: list[str] = Field(default_factory=list)
    dataset_examples: int = 0
    dependencies: list[TrainingRunnerDependency] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    log_path: str | None = None
    manifest_path: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class HardwareProfile(BaseModel):
    gpu_vram_gb: int = Field(default=0, ge=0)
    system_ram_gb: int = Field(default=16, ge=1)
    has_cuda: bool = False
    device: str = "cpu"


class ModelCandidate(BaseModel):
    model_id: str
    display_name: str
    family: str
    parameters_b: float
    min_vram_gb: int
    preferred_vram_gb: int
    context_window: int
    strengths: list[str]
    training_methods: list[str]
    runtimes: list[str]
    license_notes: str
    recommended_for: list[str]


class ModelRecommendationRequest(BaseModel):
    use_case: str = "general"
    hardware: HardwareProfile = Field(default_factory=HardwareProfile)
    prefer_quality: bool = True


class TrainingPlanRequest(BaseModel):
    use_case: str = "general"
    dataset_path: str = "training/datasets/ceibo_instructions.jsonl"
    target_runtime: str = "vllm"
    hardware: HardwareProfile = Field(default_factory=HardwareProfile)
    prefer_quality: bool = True
    train_from_scratch: bool = False


class TrainingPlanStep(BaseModel):
    order: int
    name: str
    description: str
    command: str | None = None


class TrainingPlanResponse(BaseModel):
    selected_model: ModelCandidate
    strategy: str
    dataset_path: str
    output_model_path: str
    warnings: list[str]
    steps: list[TrainingPlanStep]


class ModelVersionStatus(StrEnum):
    CANDIDATE = "candidate"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DatasetVersionRecord(BaseModel):
    version_id: str
    name: str
    path: str
    sha256: str
    examples: int
    source: str = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetVersionRequest(BaseModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    source: str = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelVersionRecord(BaseModel):
    version_id: str
    name: str
    base_model: str
    adapter_path: str | None = None
    dataset_version_id: str | None = None
    status: ModelVersionStatus = ModelVersionStatus.CANDIDATE
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelVersionRequest(BaseModel):
    name: str = Field(min_length=1)
    base_model: str = Field(min_length=1)
    adapter_path: str | None = None
    dataset_version_id: str | None = None
    status: ModelVersionStatus = ModelVersionStatus.CANDIDATE
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegistryOverview(BaseModel):
    datasets: list[DatasetVersionRecord] = Field(default_factory=list)
    models: list[ModelVersionRecord] = Field(default_factory=list)
    active_model: ModelVersionRecord | None = None


class ModelPromotionRequest(BaseModel):
    model_version_id: str = Field(min_length=1)
    approved_by: str | None = None
    min_average_score: int = Field(default=67, ge=0, le=100)
    require_dataset: bool = True
    require_evaluation: bool = True
    notes: str = ""


class PromotionGateCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ModelPromotionDecision(BaseModel):
    model_version_id: str
    approved: bool
    promoted_model: ModelVersionRecord | None = None
    checks: list[PromotionGateCheck] = Field(default_factory=list)
    evaluation_run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CoreStatus(BaseModel):
    service: str
    environment: str
    agents_online: int
    persistence_enabled: bool
    event_bus_enabled: bool
    llm_provider: str
    default_model: str
    memory_backend: str
    vector_memory_enabled: bool
    embedding_provider: str
    engine_model_id: str
    engine_mode: str
    core_directive: str


class SingularitySignal(BaseModel):
    name: str
    active: bool
    detail: str


class SingularityCategoryScore(BaseModel):
    category: str
    weight: int = Field(ge=0, le=100)
    score: int = Field(ge=0, le=100)
    weighted_score: float = Field(ge=0)
    signals: list[SingularitySignal] = Field(default_factory=list)


class SingularityIndex(BaseModel):
    index: int = Field(ge=0, le=100)
    maturity_level: str
    summary: str
    categories: list[SingularityCategoryScore]
    next_steps: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SingularitySnapshotRecord(SingularityIndex):
    snapshot_id: str
    created_at: datetime
