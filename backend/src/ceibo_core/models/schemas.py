from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


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


class DevCoreCapabilityStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    ACTIVE = "active"
    BLOCKED = "blocked"


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
    RUN_DEVCORE_PLAN = "run_devcore_plan"


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


class VoiceAuthorizationRequest(BaseModel):
    transcript: str = Field(min_length=1)
    user_id: str = "local-owner"


class VoiceAuthorizationResponse(BaseModel):
    authorized: bool
    user_id: str
    authorization_token: str | None = None
    expires_at: datetime | None = None
    mode: str = "spoken_owner_phrase"
    message: str
    safety_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceCommandRequest(BaseModel):
    transcript: str = Field(min_length=1)
    user_id: str = "local-owner"
    session_id: str | None = None
    authorization_token: str | None = None


class VoiceCommandResponse(BaseModel):
    accepted: bool
    authorized: bool
    user_id: str
    command: str | None = None
    intent: str | None = None
    risk_level: str | None = None
    policy_action: str | None = None
    cyber_category: str | None = None
    reason: str
    requires_authorization: bool = False
    requires_confirmation: bool = False
    double_confirmation_required: bool = False
    authorization_token: str | None = None
    expires_at: datetime | None = None
    safety_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceRevokeRequest(BaseModel):
    user_id: str = "local-owner"
    authorization_token: str | None = None


class VoiceRevokeResponse(BaseModel):
    revoked: bool
    user_id: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceStatusResponse(BaseModel):
    enabled: bool = True
    authorized_users: list[str] = Field(default_factory=list)
    active_sessions: dict[str, datetime] = Field(default_factory=dict)
    blocked_commands: int = 0
    mode: str = "spoken_owner_phrase"
    authorization_phrase_hint: str
    safety_notes: list[str] = Field(default_factory=list)


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
    active_capabilities: int = 0
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


class DevCoreParseRequest(BaseModel):
    message: str = Field(min_length=1)
    user_id: str = "local-user"
    context: list[str] = Field(default_factory=list)


class DevCoreParsedParameter(BaseModel):
    name: str
    value: str
    confidence: float = Field(ge=0, le=1)
    source: str = "inferred"


class DevCoreValidationIssue(BaseModel):
    severity: str
    code: str
    message: str


class DevCoreParseResponse(BaseModel):
    parse_id: str = Field(default_factory=lambda: str(uuid4()))
    original_message: str
    normalized_message: str
    intent: str
    sub_intents: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    risk_level: str
    parameters: list[DevCoreParsedParameter] = Field(default_factory=list)
    missing_parameters: list[str] = Field(default_factory=list)
    normalized_terms: dict[str, str] = Field(default_factory=dict)
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    requires_confirmation: bool = False
    double_confirmation_required: bool = False
    cyber_category: str = "general"
    policy_action: str = "allow"
    allowed_environment: str = "local_dev"
    safety_summary: str = ""
    recommended_action: str
    structured_response: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCoreSafetyPolicy(BaseModel):
    policy_id: str
    version: str
    default_environment: str
    allow_categories: list[str] = Field(default_factory=list)
    confirm_categories: list[str] = Field(default_factory=list)
    block_categories: list[str] = Field(default_factory=list)
    double_confirm_risk_levels: list[str] = Field(default_factory=list)


class DevCoreTemplateParameter(BaseModel):
    name: str
    description: str
    required: bool = True
    default: str | None = None


class DevCoreTemplateRecord(BaseModel):
    template_id: str
    name: str
    language: str
    description: str
    parameters: list[DevCoreTemplateParameter]
    safety_notes: list[str] = Field(default_factory=list)


class DevCoreTemplateRenderRequest(BaseModel):
    template_id: str = Field(min_length=1)
    parameters: dict[str, str] = Field(default_factory=dict)
    user_id: str = "local-user"


class DevCoreTemplateRenderResponse(BaseModel):
    render_id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: str
    language: str
    artifact_name: str
    content: str
    missing_parameters: list[str] = Field(default_factory=list)
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    safe_to_execute: bool = False
    requires_review: bool = True
    safety_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCoreExecutionRequest(BaseModel):
    command: str = Field(min_length=1)
    working_directory: str = "."
    user_id: str = "local-user"
    confirmation_phrase: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class DevCoreExecutionResponse(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    command: str
    working_directory: str
    status: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    risk_level: str
    cyber_category: str
    policy_action: str
    requires_confirmation: bool
    double_confirmation_required: bool
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    audit_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCorePatchPlannerRequest(BaseModel):
    goal: str = Field(min_length=1)
    user_id: str = "local-user"
    context: list[str] = Field(default_factory=list)


class DevCorePatchPlanFile(BaseModel):
    path: str
    change_type: str
    rationale: str


class DevCorePatchPlannerResponse(BaseModel):
    patch_plan_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    intent: str
    risk_level: str
    policy_action: str
    cyber_category: str
    requires_confirmation: bool
    files: list[DevCorePatchPlanFile] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    suggested_tests: list[str] = Field(default_factory=list)
    diff_preview: str = ""
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    applies_changes: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCorePatchChange(BaseModel):
    path: str = Field(min_length=1)
    content: str
    change_type: str = "modify"


class DevCorePatchApplyRequest(BaseModel):
    patch_plan_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    files: list[DevCorePatchPlanFile] = Field(default_factory=list)
    proposed_changes: list[DevCorePatchChange] = Field(default_factory=list)
    confirmation_phrase: str | None = None
    user_id: str = "local-user"


class DevCorePatchProposeRequest(BaseModel):
    patch_plan_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    files: list[DevCorePatchPlanFile] = Field(default_factory=list)
    user_id: str = "local-user"
    context: list[str] = Field(default_factory=list)


class DevCorePatchProposeResponse(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    patch_plan_id: str
    goal: str
    proposed_changes: list[DevCorePatchChange] = Field(default_factory=list)
    diff_preview: str = ""
    suggested_tests: list[str] = Field(default_factory=list)
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    applies_changes: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCorePatchApplyResponse(BaseModel):
    apply_id: str = Field(default_factory=lambda: str(uuid4()))
    patch_plan_id: str
    status: str
    risk_level: str
    policy_action: str
    cyber_category: str
    requires_confirmation: bool = True
    applied_files: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None
    suggested_tests: list[str] = Field(default_factory=list)
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    audit_notes: list[str] = Field(default_factory=list)
    applies_changes: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCorePatchRollbackRequest(BaseModel):
    snapshot_id: str = Field(min_length=1)
    confirmation_phrase: str | None = None
    user_id: str = "local-user"


class DevCorePatchRollbackResponse(BaseModel):
    rollback_id: str = Field(default_factory=lambda: str(uuid4()))
    snapshot_id: str
    status: str
    restored_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    audit_notes: list[str] = Field(default_factory=list)
    applies_changes: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevCorePatchVerifyRequest(BaseModel):
    command: str = Field(min_length=1)
    working_directory: str = "."
    user_id: str = "local-user"
    timeout_seconds: int = Field(default=60, ge=1, le=120)


class DevCorePatchVerifyResponse(BaseModel):
    verification_id: str = Field(default_factory=lambda: str(uuid4()))
    command: str
    status: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    validation_issues: list[DevCoreValidationIssue] = Field(default_factory=list)
    audit_notes: list[str] = Field(default_factory=list)
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


class AutobiographicalMemoryKind(StrEnum):
    GOAL = "goal"
    DECISION = "decision"
    PREFERENCE = "preference"
    PROJECT_STATE = "project_state"
    USER_PROFILE = "user_profile"
    SAFETY_RULE = "safety_rule"


class AutobiographicalMemoryRequest(BaseModel):
    kind: AutobiographicalMemoryKind
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=2000)
    importance: int = Field(default=70, ge=1, le=100)
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "content", "source", mode="before")
    @classmethod
    def strip_autobiographical_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value


class AutobiographicalMemoryEntry(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"auto-{uuid4().hex[:12]}")
    kind: AutobiographicalMemoryKind
    title: str
    content: str
    importance: int = Field(default=70, ge=1, le=100)
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None


class AutobiographicalMemoryState(BaseModel):
    status: str
    summary: str
    memory_path: str
    total_entries: int
    kind_counts: dict[str, int] = Field(default_factory=dict)
    important_entries: list[AutobiographicalMemoryEntry] = Field(default_factory=list)
    recent_entries: list[AutobiographicalMemoryEntry] = Field(default_factory=list)
    saved_entry: AutobiographicalMemoryEntry | None = None
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CognitiveReflectionRequest(BaseModel):
    prompt: str = Field(min_length=1)
    response: str = Field(min_length=1)
    source: str = "chat"
    user_id: str = "local-user"
    session_id: str | None = None
    intents: list[str] = Field(default_factory=list)
    used_context: bool = False
    memory_context: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt", "response", "source", "user_id", "session_id", mode="before")
    @classmethod
    def strip_reflection_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value


class CognitiveReflectionRecord(BaseModel):
    reflection_id: str = Field(default_factory=lambda: f"reflection-{uuid4().hex[:12]}")
    prompt: str
    response_preview: str
    source: str
    user_id: str
    session_id: str | None = None
    score: int = Field(ge=0, le=100)
    did_well: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    should_learn: list[str] = Field(default_factory=list)
    recommended_memory: AutobiographicalMemoryRequest | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CognitiveReflectionState(BaseModel):
    status: str
    summary: str
    reflection_path: str
    total_reflections: int
    average_score: float = 0
    latest_reflection: CognitiveReflectionRecord | None = None
    recent_reflections: list[CognitiveReflectionRecord] = Field(default_factory=list)
    recurring_missing: dict[str, int] = Field(default_factory=dict)
    recurring_learning: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class LearningEventRequest(BaseModel):
    instruction: str = Field(min_length=1)
    assistant_response: str = Field(min_length=1)
    rating: TrainingFeedbackRating = TrainingFeedbackRating.GOOD
    corrected_response: str | None = None
    source: str = "workbench"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("instruction", "assistant_response", "corrected_response", mode="before")
    @classmethod
    def strip_learning_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_learning_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            tag = str(item).strip().lower().replace(" ", "-")
            if tag and tag not in normalized:
                normalized.append(tag[:48])
        return normalized[:12]

    @model_validator(mode="after")
    def validate_learning_feedback(self) -> "LearningEventRequest":
        if self.rating == TrainingFeedbackRating.CORRECTED:
            correction = (self.corrected_response or "").strip()
            if len(correction) < 12:
                raise ValueError("corrected feedback requires a useful correction")
            if correction.lower() == self.assistant_response.lower():
                raise ValueError("corrected feedback must differ from the assistant response")
        return self


class LearningEventResponse(BaseModel):
    saved: bool
    example: TrainingExample
    summary: str
    duplicate_of: str | None = None
    quality_score: int = Field(default=0, ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class HumanFeedbackStudioRequest(BaseModel):
    instruction: str = Field(min_length=1)
    assistant_response: str = Field(min_length=1)
    rating: TrainingFeedbackRating = TrainingFeedbackRating.CORRECTED
    corrected_response: str | None = None
    intent: str | None = None
    risk_level: str | None = None
    policy_action: str | None = None
    source: str = "human_feedback_studio"
    tags: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator(
        "instruction",
        "assistant_response",
        "corrected_response",
        "intent",
        "risk_level",
        "policy_action",
        "source",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_human_feedback_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value


class HumanFeedbackStudioExample(BaseModel):
    example_id: str
    instruction: str
    response_preview: str
    rating: TrainingFeedbackRating | None = None
    source: str
    quality_score: int = Field(ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class TrainingDatasetStats(BaseModel):
    dataset_path: str
    total_examples: int
    tag_counts: dict[str, int] = Field(default_factory=dict)
    rating_counts: dict[str, int] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(default_factory=dict)
    last_updated: datetime | None = None


class HumanFeedbackStudioReport(BaseModel):
    studio_id: str = Field(default_factory=lambda: f"hf-{uuid4().hex[:10]}")
    status: str
    summary: str
    stats: TrainingDatasetStats
    recent_examples: list[HumanFeedbackStudioExample] = Field(default_factory=list)
    saved_event: LearningEventResponse | None = None
    targets: dict[str, int] = Field(default_factory=dict)
    progress: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class LearningCurationReadiness(BaseModel):
    ready: bool
    level: str
    usable_examples: int
    required_examples: int
    corrected_examples: int
    good_examples: int
    bad_examples: int
    average_score: float
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class LearningCurationReview(BaseModel):
    stats: TrainingDatasetStats
    curation: DatasetCurationReport
    readiness: LearningCurationReadiness
    recommended_min_score: int = 60


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


class DatasetExpansionRequest(BaseModel):
    target_examples: int = Field(default=100, ge=100, le=300)
    focus_areas: list[str] = Field(default_factory=list)
    difficulty: str = "balanced"
    min_quality_score: int = Field(default=80, ge=0, le=100)
    min_examples_per_category: int = Field(default=3, ge=1, le=50)
    include_robotics: bool = True
    include_code: bool = True
    include_safety: bool = True
    write_review_file: bool = True
    require_safety_signals: bool = True
    require_actionable_response: bool = True

    @field_validator("focus_areas", mode="before")
    @classmethod
    def normalize_expansion_focus(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            focus = str(item).strip().lower().replace(" ", "-")
            if focus and focus not in normalized:
                normalized.append(focus[:64])
        return normalized[:12]


class DatasetExpansionCandidate(BaseModel):
    candidate_id: str
    category: str
    quality_score: int = Field(ge=0, le=100)
    duplicate_risk: str = "low"
    fingerprint: str = ""
    requires_human_review: bool = True
    accepted_by_gate: bool = False
    example: TrainingExample
    quality_signals: list[str] = Field(default_factory=list)
    gate_failures: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)


class DatasetExpansionCategoryProfile(BaseModel):
    category: str
    candidates: int = 0
    average_quality: float = 0
    gate_passed: int = 0
    duplicates: int = 0
    top_signals: list[str] = Field(default_factory=list)
    status: str = "missing"


class DatasetExpansionQualityGate(BaseModel):
    name: str
    passed: bool
    current: int | float | str | None = None
    target: int | float | str | None = None
    severity: str = "info"
    detail: str


class DatasetExpansionReport(BaseModel):
    expansion_id: str
    status: str
    summary: str
    requested_examples: int
    generated_examples: int
    accepted_candidates: int
    rejected_candidates: int
    average_quality: float = 0
    category_counts: dict[str, int] = Field(default_factory=dict)
    coverage_score: int = Field(default=0, ge=0, le=100)
    diversity_score: int = Field(default=0, ge=0, le=100)
    duplicate_candidates: int = 0
    gate_passed_candidates: int = 0
    promotion_ready: bool = False
    dataset_fingerprint: str | None = None
    category_profiles: list[DatasetExpansionCategoryProfile] = Field(default_factory=list)
    quality_gates: list[DatasetExpansionQualityGate] = Field(default_factory=list)
    review_protocol: list[str] = Field(default_factory=list)
    review_file: str | None = None
    review_manifest: str | None = None
    preview_candidates: list[DatasetExpansionCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class EvaluationTrainingGate(BaseModel):
    allowed: bool
    level: str
    evaluation_score: int | None = None
    evaluation_status: str = "missing"
    passed_cases: int = 0
    total_cases: int = 0
    curation_ready: bool = False
    usable_examples: int = 0
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    latest_report: EvaluationSuiteReport | None = None
    curation_review: LearningCurationReview | None = None


class EvaluationRemediationItem(BaseModel):
    case_id: str
    category: str
    score: int = Field(ge=0, le=100)
    missing_signals: list[str] = Field(default_factory=list)
    diagnosis: str
    recommended_actions: list[str] = Field(default_factory=list)
    proposed_learning_example: TrainingExampleRequest


class EvaluationRemediationPlan(BaseModel):
    available: bool
    run_id: str | None = None
    status: str = "missing"
    average_score: int | None = None
    failed_cases: int = 0
    summary: str
    items: list[EvaluationRemediationItem] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class EvaluationRemediationApplyRequest(BaseModel):
    case_id: str = Field(min_length=1)
    confirmation: str = Field(min_length=1)
    corrected_response: str | None = None
    rerun_evaluation: bool = True

    @field_validator("case_id", "confirmation", "corrected_response", mode="before")
    @classmethod
    def strip_apply_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value


class EvaluationRemediationOutcome(BaseModel):
    outcome_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    status: str
    accepted: bool = False
    before_run_id: str
    after_run_id: str | None = None
    before_score: int = Field(ge=0, le=100)
    after_score: int | None = Field(default=None, ge=0, le=100)
    score_delta: int | None = None
    case_before_passed: bool | None = None
    case_after_passed: bool | None = None
    improved_cases: list[str] = Field(default_factory=list)
    degraded_cases: list[str] = Field(default_factory=list)
    unchanged_failed_cases: list[str] = Field(default_factory=list)
    recommendation: str
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationRemediationOutcomeReview(BaseModel):
    available: bool
    summary: str
    latest_outcome: EvaluationRemediationOutcome | None = None
    outcomes: list[EvaluationRemediationOutcome] = Field(default_factory=list)
    accepted_count: int = 0
    blocked_count: int = 0
    regression_count: int = 0
    pending_count: int = 0
    next_actions: list[str] = Field(default_factory=list)


class EvaluationRemediationApplyResponse(BaseModel):
    applied: bool
    case_id: str
    confirmation_required: str
    message: str
    saved_learning_event: LearningEventResponse | None = None
    before_report: EvaluationSuiteReport | None = None
    after_report: EvaluationSuiteReport | None = None
    score_delta: int | None = None
    case_before_passed: bool | None = None
    case_after_passed: bool | None = None
    promotable: bool = False
    outcome: EvaluationRemediationOutcome | None = None
    next_actions: list[str] = Field(default_factory=list)


class TrainingPromotionEvidence(BaseModel):
    latest_run_id: str | None = None
    evaluation_status: str = "missing"
    evaluation_score: int | None = None
    passed_cases: int = 0
    total_cases: int = 0
    curation_ready: bool = False
    usable_examples: int = 0
    corrected_examples: int = 0
    accepted_outcomes: int = 0
    regression_outcomes: int = 0
    pending_outcomes: int = 0
    blocked_outcomes: int = 0


class TrainingPromotionGate(BaseModel):
    allowed: bool
    level: str
    summary: str
    evidence: TrainingPromotionEvidence
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    latest_report: EvaluationSuiteReport | None = None
    curation_review: LearningCurationReview | None = None
    outcome_review: EvaluationRemediationOutcomeReview | None = None


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


class TrainingDryRunReport(BaseModel):
    run_id: str
    allowed: bool
    status: TrainingRunStatus
    summary: str
    config_path: str
    dataset_path: str
    output_dir: str
    base_model: str
    command: list[str] = Field(default_factory=list)
    dataset_examples: int = 0
    estimated_steps: int = 1
    gate: TrainingPromotionGate
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrainingEvidenceBuilderRequest(BaseModel):
    target_usable_examples: int = Field(default=25, ge=1)
    target_corrected_examples: int = Field(default=3, ge=0)
    target_evaluation_score: int = Field(default=85, ge=0, le=100)
    target_accepted_outcomes: int = Field(default=1, ge=0)
    include_candidate_examples: bool = True
    max_candidates: int = Field(default=6, ge=1, le=20)


class TrainingEvidenceGap(BaseModel):
    key: str
    label: str
    current: int | str | None = None
    target: int | str | None = None
    missing: int = 0
    severity: str
    blocking: bool = True
    description: str
    recommended_actions: list[str] = Field(default_factory=list)


class TrainingEvidenceCandidate(BaseModel):
    candidate_id: str
    kind: str
    title: str
    rationale: str
    expected_impact: list[str] = Field(default_factory=list)
    source_case_id: str | None = None
    proposed_learning_example: TrainingExampleRequest | None = None
    safe_to_apply: bool = False
    requires_human_review: bool = True
    next_actions: list[str] = Field(default_factory=list)


class TrainingEvidenceBuilderReport(BaseModel):
    builder_id: str
    status: str
    evidence_score: int = Field(ge=0, le=100)
    summary: str
    gate: TrainingPromotionGate
    gaps: list[TrainingEvidenceGap] = Field(default_factory=list)
    candidates: list[TrainingEvidenceCandidate] = Field(default_factory=list)
    remediation_plan: EvaluationRemediationPlan | None = None
    curation_review: LearningCurationReview | None = None
    outcome_review: EvaluationRemediationOutcomeReview | None = None
    next_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class DevCoreCapabilityRecord(BaseModel):
    capability_id: str
    name: str
    description: str
    status: DevCoreCapabilityStatus = DevCoreCapabilityStatus.CANDIDATE
    safety_score: int = Field(default=0, ge=0, le=100)
    evaluation_category: str = "devcore"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DevCoreCapabilityPromotionRequest(BaseModel):
    capability_id: str = Field(min_length=1)
    approved_by: str | None = None
    min_safety_score: int = Field(default=80, ge=0, le=100)
    require_evaluation: bool = True
    notes: str = ""


class DevCoreCapabilityPromotionDecision(BaseModel):
    capability_id: str
    approved: bool
    capability: DevCoreCapabilityRecord | None = None
    checks: list[PromotionGateCheck] = Field(default_factory=list)
    evaluation_run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class CognitionSignal(BaseModel):
    name: str
    active: bool
    detail: str


class CognitionLayer(BaseModel):
    layer_id: str
    name: str
    purpose: str
    score: int = Field(ge=0, le=100)
    status: str
    signals: list[CognitionSignal] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class CognitionProcessStep(BaseModel):
    order: int
    name: str
    description: str
    required_layer: str


class CognitionState(BaseModel):
    cognition_id: str = Field(default_factory=lambda: str(uuid4()))
    overall_score: int = Field(ge=0, le=100)
    maturity_level: str
    summary: str
    layers: list[CognitionLayer]
    bottlenecks: list[str] = Field(default_factory=list)
    recommended_process: list[CognitionProcessStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
