"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BrainCircuit,
  ChevronRight,
  Cpu,
  Database,
  LockKeyhole,
  Mic,
  Network,
  Radio,
  RefreshCw,
  Send,
  Shield,
  Sparkles,
  Workflow,
} from "lucide-react";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatResponse = {
  response: string;
  session_id: string;
  agent: string;
  memory_context: string[];
};

type TaskResponse = {
  task_id: string;
  status: string;
  assigned_agent: string;
  summary: string;
  orchestration_trace: OrchestrationTraceRecord | null;
  created_at: string;
};

type TaskRecord = {
  task_id: string;
  goal: string;
  status: string;
  assigned_agent: string;
  priority: number;
  created_at: string;
};

type LongRunningJobRecord = {
  job_id: string;
  kind: "generic" | "task" | "evaluation" | "training";
  title: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  current_step: string;
  task_id: string | null;
  created_at: string;
  updated_at: string;
};

type OrchestrationStep = {
  agent: string;
  action: string;
  reason: string;
  status: string;
};

type OrchestrationTraceRecord = {
  trace_id: string;
  task_id: string | null;
  user_id: string;
  goal: string;
  primary_agent: string;
  route_reason: string;
  steps: OrchestrationStep[];
  created_at: string;
};

type CoreStatus = {
  service: string;
  environment: string;
  agents_online: number;
  persistence_enabled: boolean;
  event_bus_enabled: boolean;
  llm_provider: string;
  default_model: string;
  memory_backend: string;
  vector_memory_enabled: boolean;
  embedding_provider: string;
  engine_model_id: string;
  engine_mode: string;
  core_directive: string;
};

type SecurityPolicyStatus = {
  rbac_enforced: boolean;
  local_dev_admin_enabled: boolean;
  effective_user: {
    user_id: string;
    role: "admin" | "operator" | "researcher" | "viewer";
    local_dev: boolean;
  };
  role_permissions: Record<string, string[]>;
};

type AuditEventRecord = {
  event_id: string;
  user_id: string;
  role: "admin" | "operator" | "researcher" | "viewer" | null;
  event_type: string;
  actor: string;
  action: string | null;
  allowed: boolean | null;
  payload: Record<string, unknown>;
  created_at: string;
};

type PersistenceHealth = {
  enabled: boolean;
  available: boolean;
  database_url_safe: string;
  tables: string[];
  error: string | null;
};

type KnowledgeStatus = {
  backend: string;
  total_items: number;
  sanitized_items: number;
  safety_filters: string[];
};

type SingularitySignal = {
  name: string;
  active: boolean;
  detail: string;
};

type SingularityCategoryScore = {
  category: string;
  weight: number;
  score: number;
  weighted_score: number;
  signals: SingularitySignal[];
};

type SingularityIndex = {
  index: number;
  maturity_level: string;
  summary: string;
  categories: SingularityCategoryScore[];
  next_steps: string[];
  updated_at: string;
};

type SingularitySnapshotRecord = SingularityIndex & {
  snapshot_id: string;
  created_at: string;
};

type TrainingExample = {
  example_id: string;
  instruction: string;
  input: string;
  response: string;
  tags: string[];
  source: string;
  rating: "good" | "bad" | "corrected" | null;
  created_at: string;
};

type TrainingDatasetStats = {
  dataset_path: string;
  total_examples: number;
  tag_counts: Record<string, number>;
  rating_counts: Record<string, number>;
  source_counts: Record<string, number>;
  last_updated: string | null;
};

type DatasetCurationIssue = {
  line_number: number | null;
  example_id: string | null;
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
};

type DatasetCurationReport = {
  source_path: string;
  output_path: string | null;
  total_lines: number;
  parsed_examples: number;
  kept_examples: number;
  dropped_examples: number;
  invalid_lines: number;
  duplicate_examples: number;
  average_score: number;
  score_buckets: Record<string, number>;
  issues: DatasetCurationIssue[];
  created_at: string;
};

type TeacherStatus = {
  provider: string;
  base_url: string;
  model: string;
  available: boolean;
  installed_models: string[];
  error: string | null;
};

type TeacherReviewResponse = {
  prompt: string;
  ceibo_response: string;
  teacher_model: string;
  score: number;
  passed: boolean;
  issues: string[];
  strengths: string[];
  ideal_response: string;
  saved_example: TrainingExample | null;
};

type EvaluationCaseResult = {
  case_id: string;
  category: string;
  prompt: string;
  passed: boolean;
  score: number;
  expected_signals: string[];
  observed_signals: string[];
  response_preview: string;
  notes: string[];
};

type EvaluationSuiteReport = {
  run_id: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  average_score: number;
  category_scores: Record<string, number>;
  results: EvaluationCaseResult[];
  created_at: string;
};

type DatasetVersionRecord = {
  version_id: string;
  name: string;
  path: string;
  sha256: string;
  examples: number;
  source: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type ModelVersionRecord = {
  version_id: string;
  name: string;
  base_model: string;
  adapter_path: string | null;
  dataset_version_id: string | null;
  status: "candidate" | "evaluating" | "approved" | "active" | "archived";
  metrics: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

type RegistryOverview = {
  datasets: DatasetVersionRecord[];
  models: ModelVersionRecord[];
  active_model: ModelVersionRecord | null;
};

type PromotionGateCheck = {
  name: string;
  passed: boolean;
  detail: string;
};

type ModelPromotionDecision = {
  model_version_id: string;
  approved: boolean;
  promoted_model: ModelVersionRecord | null;
  checks: PromotionGateCheck[];
  evaluation_run_id: string | null;
  created_at: string;
};

type TrainingRunnerReport = {
  run_id: string;
  status: "ready" | "blocked" | "running" | "completed" | "failed";
  config_path: string;
  dataset_path: string;
  output_dir: string;
  base_model: string;
  dataset_examples: number;
  missing_requirements: string[];
  warnings: string[];
  log_path: string | null;
  manifest_path: string | null;
};

const agents = [
  { name: "CORE", icon: BrainCircuit, status: "online", signal: "99.8%" },
  { name: "Infra", icon: Cpu, status: "standby", signal: "K8s" },
  { name: "Security", icon: Shield, status: "standby", signal: "RBAC" },
  { name: "Voice", icon: Mic, status: "standby", signal: "STT" },
  { name: "Automation", icon: Workflow, status: "standby", signal: "Jobs" },
  { name: "Telemetry", icon: Activity, status: "online", signal: "Live" },
];

const systemMetrics = [
  { label: "FastAPI", value: "ready", icon: Network },
  { label: "Qdrant", value: "armed", icon: Database },
  { label: "NATS", value: "linked", icon: Radio },
  { label: "Policy", value: "locked", icon: LockKeyhole },
];

const starterPrompts = [
  "Resume el estado del sistema CEIBO CORE.",
  "Que agentes estan disponibles y para que sirve cada uno?",
  "Como puedo entrenar mi propio motor CEIBO local?",
];

export default function Home() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8765";
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "CEIBO CORE online. El orquestador esta listo para coordinar agentes, memoria y tareas.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [connectionState, setConnectionState] = useState<"ready" | "thinking" | "offline">("ready");
  const [lastAgent, setLastAgent] = useState("core_orchestrator");
  const [memoryCount, setMemoryCount] = useState(0);
  const [taskGoal, setTaskGoal] = useState("");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [longRunningJobs, setLongRunningJobs] = useState<LongRunningJobRecord[]>([]);
  const [orchestrationTraces, setOrchestrationTraces] = useState<OrchestrationTraceRecord[]>([]);
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [coreStatus, setCoreStatus] = useState<CoreStatus | null>(null);
  const [securityStatus, setSecurityStatus] = useState<SecurityPolicyStatus | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEventRecord[]>([]);
  const [persistenceHealth, setPersistenceHealth] = useState<PersistenceHealth | null>(null);
  const [knowledgeStatus, setKnowledgeStatus] = useState<KnowledgeStatus | null>(null);
  const [singularityIndex, setSingularityIndex] = useState<SingularityIndex | null>(null);
  const [singularityHistory, setSingularityHistory] = useState<SingularitySnapshotRecord[]>([]);
  const [isCapturingSnapshot, setIsCapturingSnapshot] = useState(false);
  const [trainingExamples, setTrainingExamples] = useState<TrainingExample[]>([]);
  const [trainingStats, setTrainingStats] = useState<TrainingDatasetStats | null>(null);
  const [correction, setCorrection] = useState("");
  const [isSavingTraining, setIsSavingTraining] = useState(false);
  const [trainingNotice, setTrainingNotice] = useState("");
  const [curationReport, setCurationReport] = useState<DatasetCurationReport | null>(null);
  const [isCurating, setIsCurating] = useState(false);
  const [teacherStatus, setTeacherStatus] = useState<TeacherStatus | null>(null);
  const [teacherReview, setTeacherReview] = useState<TeacherReviewResponse | null>(null);
  const [evaluationReport, setEvaluationReport] = useState<EvaluationSuiteReport | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [registryOverview, setRegistryOverview] = useState<RegistryOverview | null>(null);
  const [isBootstrappingRegistry, setIsBootstrappingRegistry] = useState(false);
  const [promotionDecision, setPromotionDecision] = useState<ModelPromotionDecision | null>(null);
  const [isPromotingModel, setIsPromotingModel] = useState(false);
  const [teacherTopic, setTeacherTopic] = useState("CEIBO CORE entrenamiento local");
  const [isTeacherRunning, setIsTeacherRunning] = useState(false);
  const [trainingRun, setTrainingRun] = useState<TrainingRunnerReport | null>(null);
  const [isQloraRunning, setIsQloraRunning] = useState(false);

  const latestResponse = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant")?.content,
    [messages],
  );

  const latestTrainingPair = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const assistantMessage = messages[index];
      if (assistantMessage.role !== "assistant") {
        continue;
      }
      for (let userIndex = index - 1; userIndex >= 0; userIndex -= 1) {
        const userMessage = messages[userIndex];
        if (userMessage.role === "user") {
          return {
            instruction: userMessage.content,
            response: assistantMessage.content,
          };
        }
      }
    }
    return null;
  }, [messages]);

  const liveMetrics = useMemo(
    () => [
      { label: "Agents", value: String(coreStatus?.agents_online ?? 8), icon: Network },
      {
        label: "Memory",
        value: coreStatus?.memory_backend ?? "local",
        icon: Database,
      },
      {
        label: "Events",
        value: coreStatus?.event_bus_enabled ? "NATS" : "local",
        icon: Radio,
      },
      {
        label: "Dataset",
        value: String(trainingStats?.total_examples ?? 0),
        icon: LockKeyhole,
      },
    ],
    [coreStatus, trainingStats],
  );

  const singularityProgress = singularityIndex?.index ?? 0;

  const singularityMilestones = useMemo(() => {
    const scoreFor = (category: string) =>
      singularityIndex?.categories.find((item) => item.category === category)?.score ?? 0;
    return [
      { label: "Multiagente", value: `${scoreFor("Capacidad multiagente")}/100` },
      { label: "Memoria", value: `${scoreFor("Memoria")}/100` },
      { label: "Training", value: `${scoreFor("Entrenamiento propio")}/100` },
      { label: "Seguridad", value: `${scoreFor("Seguridad")}/100` },
    ];
  }, [singularityIndex]);

  const promotableModel = useMemo(
    () =>
      registryOverview?.models.find(
        (model) =>
          model.status === "candidate" ||
          model.status === "evaluating" ||
          model.status === "approved",
      ) ?? null,
    [registryOverview],
  );

  useEffect(() => {
    void refreshOperations();
  }, []);

  async function refreshOperations() {
    try {
      const [
        statusResponse,
        persistenceResponse,
        knowledgeResponse,
        securityResponse,
        auditResponse,
        singularityResponse,
        singularityHistoryResponse,
        tasksResponse,
        jobsResponse,
        orchestrationResponse,
        examplesResponse,
        statsResponse,
        teacherStatusResponse,
        evaluationResponse,
        registryResponse,
      ] = await Promise.all([
        fetch(`${apiUrl}/api/v1/status`),
        fetch(`${apiUrl}/health/persistence`),
        fetch(`${apiUrl}/api/v1/memory/knowledge/status`),
        fetch(`${apiUrl}/api/v1/status/security`),
        fetch(`${apiUrl}/api/v1/status/audit?limit=6`),
        fetch(`${apiUrl}/api/v1/status/singularity-index`),
        fetch(`${apiUrl}/api/v1/status/singularity-index/history?limit=6`),
        fetch(`${apiUrl}/api/v1/tasks`),
        fetch(`${apiUrl}/api/v1/tasks/jobs?limit=4`),
        fetch(`${apiUrl}/api/v1/agents/orchestration/recent?limit=4`),
        fetch(`${apiUrl}/api/v1/engine/training/examples?limit=5`),
        fetch(`${apiUrl}/api/v1/engine/training/stats`),
        fetch(`${apiUrl}/api/v1/engine/teacher/status`),
        fetch(`${apiUrl}/api/v1/engine/evaluations/latest`),
        fetch(`${apiUrl}/api/v1/engine/registry?limit=6`),
      ]);
      if (statusResponse.ok) {
        setCoreStatus((await statusResponse.json()) as CoreStatus);
      }
      if (persistenceResponse.ok) {
        setPersistenceHealth((await persistenceResponse.json()) as PersistenceHealth);
      }
      if (knowledgeResponse.ok) {
        setKnowledgeStatus((await knowledgeResponse.json()) as KnowledgeStatus);
      }
      if (securityResponse.ok) {
        setSecurityStatus((await securityResponse.json()) as SecurityPolicyStatus);
      }
      if (auditResponse.ok) {
        setAuditEvents((await auditResponse.json()) as AuditEventRecord[]);
      }
      if (singularityResponse.ok) {
        setSingularityIndex((await singularityResponse.json()) as SingularityIndex);
      }
      if (singularityHistoryResponse.ok) {
        setSingularityHistory(
          (await singularityHistoryResponse.json()) as SingularitySnapshotRecord[],
        );
      }
      if (tasksResponse.ok) {
        setTasks((await tasksResponse.json()) as TaskRecord[]);
      }
      if (jobsResponse.ok) {
        setLongRunningJobs((await jobsResponse.json()) as LongRunningJobRecord[]);
      }
      if (orchestrationResponse.ok) {
        setOrchestrationTraces(
          (await orchestrationResponse.json()) as OrchestrationTraceRecord[],
        );
      }
      if (examplesResponse.ok) {
        setTrainingExamples((await examplesResponse.json()) as TrainingExample[]);
      }
      if (statsResponse.ok) {
        setTrainingStats((await statsResponse.json()) as TrainingDatasetStats);
      }
      if (teacherStatusResponse.ok) {
        setTeacherStatus((await teacherStatusResponse.json()) as TeacherStatus);
      }
      if (evaluationResponse.ok) {
        const result = await evaluationResponse.json();
        setEvaluationReport(result as EvaluationSuiteReport | null);
      }
      if (registryResponse.ok) {
        setRegistryOverview((await registryResponse.json()) as RegistryOverview);
      }
      await refreshAuditEvents();
    } catch {
      setConnectionState("offline");
    }
  }

  async function refreshAuditEvents() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/status/audit?limit=6`);
      if (response.ok) {
        setAuditEvents((await response.json()) as AuditEventRecord[]);
      }
    } catch {
      // Keep the last visible audit state.
    }
  }

  async function bootstrapRegistry() {
    if (isBootstrappingRegistry) {
      return;
    }

    setIsBootstrappingRegistry(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/registry/bootstrap`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }
      const overview = (await response.json()) as RegistryOverview;
      setRegistryOverview(overview);
      setTrainingNotice(
        `Registry actualizado: ${overview.datasets.length} datasets, ${overview.models.length} modelos.`,
      );
      const singularityResponse = await fetch(`${apiUrl}/api/v1/status/singularity-index`);
      if (singularityResponse.ok) {
        setSingularityIndex((await singularityResponse.json()) as SingularityIndex);
      }
      await refreshAuditEvents();
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude inicializar el Model/Dataset Registry.");
    } finally {
      setIsBootstrappingRegistry(false);
    }
  }

  async function promoteCandidateModel() {
    if (!promotableModel || isPromotingModel) {
      return;
    }

    setIsPromotingModel(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/registry/models/promote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_version_id: promotableModel.version_id,
          approved_by: "local-admin",
          min_average_score: 67,
          require_dataset: true,
          require_evaluation: true,
          notes: "Promocion desde dashboard local",
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }
      const decision = (await response.json()) as ModelPromotionDecision;
      setPromotionDecision(decision);
      setTrainingNotice(
        decision.approved
          ? `Modelo promovido: ${decision.promoted_model?.name ?? promotableModel.name}.`
          : "Promotion Gate bloqueo la promocion.",
      );
      const registryResponse = await fetch(`${apiUrl}/api/v1/engine/registry?limit=6`);
      if (registryResponse.ok) {
        setRegistryOverview((await registryResponse.json()) as RegistryOverview);
      }
      const singularityResponse = await fetch(`${apiUrl}/api/v1/status/singularity-index`);
      if (singularityResponse.ok) {
        setSingularityIndex((await singularityResponse.json()) as SingularityIndex);
      }
      await refreshAuditEvents();
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude ejecutar el Promotion Gate.");
    } finally {
      setIsPromotingModel(false);
    }
  }

  async function runEvaluationSuite() {
    if (isEvaluating) {
      return;
    }

    setIsEvaluating(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/evaluations/run`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }
      const report = (await response.json()) as EvaluationSuiteReport;
      setEvaluationReport(report);
      setTrainingNotice(`Evaluation Harness: ${report.average_score}/100.`);

      const singularityResponse = await fetch(`${apiUrl}/api/v1/status/singularity-index`);
      if (singularityResponse.ok) {
        setSingularityIndex((await singularityResponse.json()) as SingularityIndex);
      }
      await refreshAuditEvents();
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude ejecutar el Evaluation Harness.");
    } finally {
      setIsEvaluating(false);
    }
  }

  async function captureSingularitySnapshot() {
    if (isCapturingSnapshot) {
      return;
    }

    setIsCapturingSnapshot(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/status/singularity-index/snapshots`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }
      const snapshot = (await response.json()) as SingularitySnapshotRecord;
      setSingularityHistory((current) => [snapshot, ...current].slice(0, 6));
      setSingularityIndex(snapshot);
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
    } finally {
      setIsCapturingSnapshot(false);
    }
  }

  async function sendMessage(nextMessage?: string) {
    const content = (nextMessage ?? input).trim();
    if (!content || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);
    setConnectionState("thinking");
    setMessages((current) => [...current, { role: "user", content }]);

    try {
      const response = await fetch(`${apiUrl}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          user_id: "local-user",
        }),
      });

      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const data = (await response.json()) as ChatResponse;
      setSessionId(data.session_id);
      setLastAgent(data.agent);
      setMemoryCount(data.memory_context?.length ?? 0);
      setMessages((current) => [...current, { role: "assistant", content: data.response }]);
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "No pude conectar con la API local. Inicia el backend en el puerto 8765 y vuelvo a operar en tiempo real.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const goal = taskGoal.trim();
    if (!goal || isCreatingTask) {
      return;
    }

    setIsCreatingTask(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          goal,
          user_id: "local-user",
          priority: 5,
          metadata: {
            long_running: /entrena|training|qlora|evaluation|evaluacion/i.test(goal),
          },
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const data = (await response.json()) as TaskResponse;
      setTaskGoal("");
      setLastAgent(data.assigned_agent);
      if (data.orchestration_trace) {
        setOrchestrationTraces((current) => [data.orchestration_trace!, ...current].slice(0, 4));
      }
      setTasks((current) => [
        {
          task_id: data.task_id,
          goal,
          status: data.status,
          assigned_agent: data.assigned_agent,
          priority: 5,
          created_at: data.created_at,
        },
        ...current,
      ]);
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
    } finally {
      setIsCreatingTask(false);
    }
  }

  async function saveTrainingFeedback(rating: "good" | "corrected") {
    if (!latestTrainingPair || isSavingTraining) {
      return;
    }

    const correctedResponse = correction.trim();
    if (rating === "corrected" && !correctedResponse) {
      setTrainingNotice("Escribe la respuesta corregida antes de guardarla.");
      return;
    }

    setIsSavingTraining(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/training/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: latestTrainingPair.instruction,
          original_response: latestTrainingPair.response,
          corrected_response: rating === "corrected" ? correctedResponse : undefined,
          rating,
          tags: ["dashboard", "trainer"],
          source: "dashboard",
          metadata: {
            session_id: sessionId,
            agent: lastAgent,
          },
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const savedExample = (await response.json()) as TrainingExample;
      setTrainingExamples((current) => [...current, savedExample].slice(-5));
      setCurationReport(null);
      setCorrection("");
      setTrainingNotice(
        rating === "corrected" ? "Correccion guardada en el dataset." : "Respuesta guardada.",
      );

      const statsResponse = await fetch(`${apiUrl}/api/v1/engine/training/stats`);
      if (statsResponse.ok) {
        setTrainingStats((await statsResponse.json()) as TrainingDatasetStats);
      }
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude guardar el ejemplo en el backend local.");
    } finally {
      setIsSavingTraining(false);
    }
  }

  async function runDatasetCuration(mode: "preview" | "export") {
    if (isCurating) {
      return;
    }

    setIsCurating(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/training/curate/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          min_score: 60,
          include_bad_rated: false,
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const report = (await response.json()) as DatasetCurationReport;
      setCurationReport(report);
      setTrainingNotice(
        mode === "export"
          ? `Dataset curado exportado: ${report.kept_examples} ejemplos.`
          : `Analisis listo: ${report.kept_examples} ejemplos pasan calidad.`,
      );
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude curar el dataset desde la API local.");
    } finally {
      setIsCurating(false);
    }
  }

  async function runTeacherReview() {
    if (!latestTrainingPair || isTeacherRunning) {
      return;
    }

    setIsTeacherRunning(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/teacher/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: latestTrainingPair.instruction,
          ceibo_response: latestTrainingPair.response,
          expected_traits: [
            "explica con claridad",
            "da pasos accionables",
            "ayuda y ensena al usuario principal",
          ],
          category: "training",
          save_to_dataset: true,
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const review = (await response.json()) as TeacherReviewResponse;
      setTeacherReview(review);
      if (review.saved_example) {
        setTrainingExamples((current) =>
          [...current, review.saved_example as TrainingExample].slice(-5),
        );
      }
      setCurationReport(null);
      setTrainingNotice(`Mistral reviso la respuesta: score ${review.score}/100.`);

      const statsResponse = await fetch(`${apiUrl}/api/v1/engine/training/stats`);
      if (statsResponse.ok) {
        setTrainingStats((await statsResponse.json()) as TrainingDatasetStats);
      }
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude conectar con Mistral en Ollama.");
    } finally {
      setIsTeacherRunning(false);
    }
  }

  async function generateTeacherExamples() {
    const topic = teacherTopic.trim();
    if (!topic || isTeacherRunning) {
      return;
    }

    setIsTeacherRunning(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/teacher/synthetic-examples`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          count: 2,
          difficulty: "intermediate",
          tags: ["teacher", "synthetic", "mistral"],
          save_to_dataset: true,
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const result = (await response.json()) as { examples: TrainingExample[]; saved_count: number };
      setTrainingExamples((current) => [...current, ...result.examples].slice(-5));
      setCurationReport(null);
      setTrainingNotice(`Mistral genero ${result.saved_count} ejemplos para el dataset.`);

      const statsResponse = await fetch(`${apiUrl}/api/v1/engine/training/stats`);
      if (statsResponse.ok) {
        setTrainingStats((await statsResponse.json()) as TrainingDatasetStats);
      }
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude generar ejemplos con Mistral en Ollama.");
    } finally {
      setIsTeacherRunning(false);
    }
  }

  async function runQloraAction(mode: "preflight" | "start") {
    if (isQloraRunning) {
      return;
    }

    setIsQloraRunning(true);
    setTrainingNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/training/qlora/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          config_path: "training/configs/ceibo_qlora.local.json",
          max_steps: 1,
          local_files_only: false,
        }),
      });
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const report = (await response.json()) as TrainingRunnerReport;
      setTrainingRun(report);
      setTrainingNotice(
        mode === "start"
          ? `QLoRA job ${report.run_id} iniciado: ${report.status}.`
          : `Preflight QLoRA: ${report.status}.`,
      );
      await refreshAuditEvents();
      setConnectionState("ready");
    } catch {
      setConnectionState("offline");
      setTrainingNotice("No pude ejecutar el Training Runner QLoRA.");
    } finally {
      setIsQloraRunning(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage();
  }

  return (
    <main className="ceibo-light min-h-screen overflow-hidden bg-[#f6f8fb] text-slate-950">
      <div className="ceibo-shell">
        <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-7 lg:px-10">
          <header className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/8 shadow-[0_0_40px_rgba(79,221,255,0.18)]">
                <Sparkles className="h-5 w-5 text-[#8be9ff]" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.32em] text-[#8be9ff]">AI Operations</p>
                <h1 className="text-xl font-semibold tracking-normal">CEIBO CORE</h1>
              </div>
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-emerald-300/25 bg-emerald-300/8 px-4 py-2 text-sm text-emerald-200 shadow-[0_0_30px_rgba(52,211,153,0.12)] sm:flex">
              <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,255,190,0.9)]" />
              {connectionState === "thinking" ? "Core thinking" : "Core online"}
            </div>
          </header>

          <div className="grid flex-1 items-start gap-8 py-10 lg:grid-cols-[0.82fr_1.18fr]">
            <section className="flex min-h-[72vh] flex-col justify-center space-y-7">
              <div className="max-w-3xl">
                <p className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/7 px-4 py-2 text-sm text-slate-300 backdrop-blur">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#8be9ff]" />
                  Horizonte de singularidad activo
                </p>
                <h2 className="mt-7 text-4xl font-semibold leading-[1.02] tracking-normal text-white md:text-6xl xl:text-7xl">
                  El estado de la Inteligencia actual a fin de alcanzar la singularidad
                </h2>
                <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
                  CEIBO CORE observa agentes, memoria, dataset, entrenamiento y capacidad local
                  para medir cuanto falta hacia una inteligencia mas autonoma, util y entrenable.
                </p>
              </div>

              <div className="hidden grid gap-3 sm:grid-cols-4">
                {liveMetrics.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.label}
                      className="rounded-2xl border border-white/10 bg-white/7 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-xl"
                    >
                      <Icon className="h-5 w-5 text-[#8be9ff]" />
                      <p className="mt-4 text-sm text-slate-400">{item.label}</p>
                      <p className="mt-1 text-2xl font-semibold text-white">{item.value}</p>
                    </div>
                  );
                })}
              </div>

              <div className="hidden rounded-[1.75rem] border border-white/12 bg-white/7 p-4 shadow-[0_30px_100px_rgba(0,0,0,0.28)] backdrop-blur-2xl">
                <div className="flex items-center justify-between px-1 pb-3">
                  <div>
                    <h3 className="text-lg font-semibold">Command center</h3>
                    <p className="text-sm text-slate-400">Chat real conectado al CORE Orchestrator</p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs ${
                      connectionState === "offline"
                        ? "bg-red-300/10 text-red-200"
                        : "bg-emerald-300/10 text-emerald-200"
                    }`}
                  >
                    {connectionState}
                  </span>
                </div>

                <div className="max-h-[300px] min-h-[260px] overflow-y-auto rounded-[1.25rem] border border-white/10 bg-black/25 p-4">
                  <div className="space-y-3">
                    {messages.map((message, index) => (
                      <div
                        key={`${message.role}-${index}`}
                        className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[86%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                            message.role === "user"
                              ? "bg-white text-slate-950"
                              : "border border-white/10 bg-white/8 text-slate-100"
                          }`}
                        >
                          {message.content}
                        </div>
                      </div>
                    ))}
                    {isSending ? (
                      <div className="w-fit rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-slate-300">
                        CORE procesando...
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {starterPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => void sendMessage(prompt)}
                      className="rounded-full border border-white/10 bg-white/7 px-3 py-2 text-xs text-slate-300 transition hover:bg-white/12"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>

                <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
                  <input
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Escribe una orden para CEIBO CORE..."
                    className="min-w-0 flex-1 rounded-full border border-white/12 bg-white/8 px-5 py-3 text-sm text-white outline-none backdrop-blur placeholder:text-slate-500 focus:border-[#8be9ff]/60"
                  />
                  <button
                    type="submit"
                    disabled={isSending}
                    className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white text-slate-950 transition hover:bg-[#dff8ff] disabled:opacity-50"
                    aria-label="Enviar mensaje"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </form>
              </div>
            </section>

            <section className="relative rounded-[2rem] border border-white/12 bg-white/7 p-5 shadow-[0_30px_120px_rgba(0,0,0,0.45)] backdrop-blur-2xl">
              <div className="absolute inset-0 rounded-[2rem] border border-white/5" />
              <div className="relative grid h-full gap-5">
                <div className="relative min-h-[440px] overflow-hidden rounded-[1.5rem] border border-white/10 bg-[#070b13]">
                  <div className="core-grid" />
                  <div className="core-horizon" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="core-system">
                      <div className="core-ring core-ring-one" />
                      <div className="core-ring core-ring-two" />
                      <div className="core-ring core-ring-three" />
                      <div className="core-center">
                        <BrainCircuit className="h-10 w-10 text-white" />
                      </div>
                    </div>
                  </div>
                  <div className="absolute left-5 top-5 rounded-full border border-white/12 bg-black/30 px-4 py-2 text-xs uppercase tracking-[0.24em] text-[#8be9ff] backdrop-blur">
                    Cerebro electronico
                  </div>
                  <div className="absolute bottom-5 left-5 right-5 grid grid-cols-3 gap-3">
                    {[
                      `Agent ${lastAgent.replace("_", " ")}`,
                      `Context ${memoryCount}`,
                      coreStatus?.engine_mode ?? "rules+rag",
                    ].map((item) => (
                      <div
                        key={item}
                        className="rounded-xl border border-white/10 bg-white/8 px-3 py-3 text-center text-xs text-slate-300 backdrop-blur"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
                  <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Medidor de singularidad</p>
                      <h3 className="mt-1 text-2xl font-semibold text-white">
                        {singularityProgress}% hacia la Singularidad
                      </h3>
                      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                        {singularityIndex?.summary ??
                          "Esperando metricas reales del backend para calcular el indice."}
                      </p>
                    </div>
                    <span className="rounded-full border border-[#8be9ff]/25 bg-[#8be9ff]/10 px-4 py-2 text-sm font-medium text-[#8be9ff]">
                      {singularityIndex?.maturity_level ?? "sync"}
                    </span>
                  </div>

                  <div className="mt-5 h-4 overflow-hidden rounded-full border border-white/12 bg-white/40">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#23d9ff] via-[#0ea5e9] to-[#45f5a5] shadow-[0_0_30px_rgba(35,217,255,0.36)] transition-all duration-700"
                      style={{ width: `${singularityProgress}%` }}
                    />
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-4">
                    {singularityMilestones.map((item) => (
                      <div
                        key={item.label}
                        className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                      >
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          {item.label}
                        </p>
                        <p className="mt-2 line-clamp-1 text-sm font-semibold text-slate-100">
                          {item.value}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-3">
                    {(singularityIndex?.categories ?? []).slice(0, 6).map((item) => (
                      <div
                        key={item.category}
                        className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="line-clamp-1 text-sm font-medium text-slate-200">
                            {item.category}
                          </p>
                          <span className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-slate-300">
                            {item.score}
                          </span>
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                          <div
                            className="h-full rounded-full bg-[#8be9ff]"
                            style={{ width: `${item.score}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          Historico
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          Snapshots del indice para medir evolucion por sprint.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void captureSingularitySnapshot()}
                        disabled={isCapturingSnapshot}
                        className="rounded-full border border-[#8be9ff]/25 bg-[#8be9ff]/10 px-4 py-2 text-sm text-[#dff8ff] transition hover:bg-[#8be9ff]/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Capturar estado
                      </button>
                    </div>

                    <div className="mt-4 grid gap-2 sm:grid-cols-3">
                      {singularityHistory.length === 0 ? (
                        <p className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3 text-sm text-slate-400 sm:col-span-3">
                          Todavia no hay snapshots. Captura el primer estado para iniciar la serie.
                        </p>
                      ) : (
                        singularityHistory.map((snapshot) => (
                          <div
                            key={snapshot.snapshot_id}
                            className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-lg font-semibold text-white">{snapshot.index}%</p>
                              <span className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-slate-300">
                                {snapshot.maturity_level}
                              </span>
                            </div>
                            <p className="mt-2 line-clamp-1 text-xs text-slate-500">
                              {new Date(snapshot.created_at).toLocaleString()}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          Evaluation Harness
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          Pruebas reproducibles de razonamiento, RAG y seguridad.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void runEvaluationSuite()}
                        disabled={isEvaluating}
                        className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Ejecutar evals
                      </button>
                    </div>

                    {evaluationReport ? (
                      <div className="mt-4 space-y-3">
                        <div className="grid gap-2 sm:grid-cols-4">
                          {[
                            ["Score", `${evaluationReport.average_score}/100`],
                            ["Casos", `${evaluationReport.passed_cases}/${evaluationReport.total_cases}`],
                            ["Estado", evaluationReport.status],
                            ["Run", evaluationReport.run_id.split("-").slice(0, 2).join("-")],
                          ].map(([label, value]) => (
                            <div
                              key={label}
                              className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                            >
                              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                                {label}
                              </p>
                              <p className="mt-2 line-clamp-1 text-sm font-semibold text-slate-100">
                                {value}
                              </p>
                            </div>
                          ))}
                        </div>

                        <div className="grid gap-2 sm:grid-cols-3">
                          {Object.entries(evaluationReport.category_scores).map(
                            ([category, score]) => (
                              <div
                                key={category}
                                className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <p className="text-sm font-medium capitalize text-slate-200">
                                    {category}
                                  </p>
                                  <span className="text-sm text-slate-300">{score}</span>
                                </div>
                                <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                                  <div
                                    className="h-full rounded-full bg-emerald-300"
                                    style={{ width: `${score}%` }}
                                  />
                                </div>
                              </div>
                            ),
                          )}
                        </div>

                        <div className="space-y-2">
                          {evaluationReport.results.slice(0, 4).map((result) => (
                            <div
                              key={result.case_id}
                              className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <p className="line-clamp-1 text-sm font-medium text-slate-100">
                                  {result.case_id}
                                </p>
                                <span
                                  className={`rounded-full px-2.5 py-1 text-xs ${
                                    result.passed
                                      ? "bg-emerald-300/10 text-emerald-200"
                                      : "bg-amber-300/10 text-amber-200"
                                  }`}
                                >
                                  {result.score}
                                </span>
                              </div>
                              <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                                {result.response_preview}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="mt-4 rounded-2xl border border-white/10 bg-white/7 px-3 py-3 text-sm text-slate-400">
                        Todavia no hay evaluaciones. Ejecuta el primer suite para crear baseline.
                      </p>
                    )}
                  </div>

                  <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          Model/Dataset Registry
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          Versionado inicial de datasets, adapters y modelo activo.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void bootstrapRegistry()}
                        disabled={isBootstrappingRegistry}
                        className="rounded-full border border-[#8be9ff]/25 bg-[#8be9ff]/10 px-4 py-2 text-sm text-[#dff8ff] transition hover:bg-[#8be9ff]/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Inicializar registry
                      </button>
                      <button
                        type="button"
                        onClick={() => void promoteCandidateModel()}
                        disabled={!promotableModel || isPromotingModel}
                        className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Promover modelo
                      </button>
                    </div>

                    <div className="mt-4 grid gap-2 sm:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                          Datasets
                        </p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {registryOverview?.datasets.length ?? 0}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                          Modelos
                        </p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {registryOverview?.models.length ?? 0}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                          Activo
                        </p>
                        <p className="mt-2 line-clamp-1 text-sm font-semibold text-white">
                          {registryOverview?.active_model?.name ?? "sin promover"}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 rounded-2xl border border-white/10 bg-white/7 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                            RBAC
                          </p>
                          <p className="mt-1 text-sm text-slate-300">
                            {securityStatus?.effective_user.user_id ?? "sync"} /{" "}
                            {securityStatus?.effective_user.role ?? "sync"}
                          </p>
                        </div>
                        <span className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-slate-300">
                          {securityStatus?.rbac_enforced ? "enforced" : "local-dev"}
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 rounded-2xl border border-white/10 bg-white/7 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                            Persistencia
                          </p>
                          <p className="mt-1 line-clamp-1 text-sm text-slate-300">
                            {persistenceHealth?.database_url_safe ?? "sync"}
                          </p>
                        </div>
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs ${
                            persistenceHealth?.available
                              ? "bg-emerald-300/10 text-emerald-200"
                              : "bg-amber-300/10 text-amber-200"
                          }`}
                        >
                          {persistenceHealth?.available
                            ? `${persistenceHealth.tables.length} tables`
                            : persistenceHealth?.enabled
                              ? "offline"
                              : "local"}
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 rounded-2xl border border-white/10 bg-white/7 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                            Knowledge Base
                          </p>
                          <p className="mt-1 text-sm text-slate-300">
                            {knowledgeStatus?.backend ?? "sync"} /{" "}
                            {knowledgeStatus?.safety_filters.length ?? 0} filtros
                          </p>
                        </div>
                        <span className="rounded-full bg-cyan-300/10 px-2.5 py-1 text-xs text-cyan-100">
                          {knowledgeStatus?.total_items ?? 0} items
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 rounded-2xl border border-white/10 bg-white/7 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                            Audit Trail
                          </p>
                          <p className="mt-1 text-sm text-slate-300">
                            Acciones sensibles recientes
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void refreshAuditEvents()}
                          className="rounded-full border border-white/12 bg-white/8 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/12"
                        >
                          Actualizar
                        </button>
                      </div>
                      <div className="mt-3 space-y-2">
                        {auditEvents.length === 0 ? (
                          <p className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-500">
                            Aun no hay eventos auditados en esta sesion.
                          </p>
                        ) : (
                          auditEvents.slice(0, 5).map((event) => (
                            <div
                              key={event.event_id}
                              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <p className="line-clamp-1 text-xs font-medium text-slate-200">
                                  {event.event_type}
                                </p>
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[11px] ${
                                    event.allowed === false
                                      ? "bg-red-300/10 text-red-200"
                                      : "bg-emerald-300/10 text-emerald-200"
                                  }`}
                                >
                                  {event.allowed === false ? "denied" : "ok"}
                                </span>
                              </div>
                              <p className="mt-1 line-clamp-1 text-xs text-slate-500">
                                {event.user_id} / {event.role ?? "unknown"} /{" "}
                                {event.action ?? event.actor}
                              </p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                      <div className="space-y-2">
                        {(registryOverview?.datasets ?? []).slice(0, 4).map((dataset) => (
                          <div
                            key={dataset.version_id}
                            className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="line-clamp-1 text-sm font-medium text-slate-100">
                                {dataset.name}
                              </p>
                              <span className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-slate-300">
                                {dataset.examples}
                              </span>
                            </div>
                            <p className="mt-2 line-clamp-1 text-xs text-slate-500">
                              {dataset.sha256.slice(0, 12)} - {dataset.source}
                            </p>
                          </div>
                        ))}
                      </div>

                      <div className="space-y-2">
                        {(registryOverview?.models ?? []).slice(0, 4).map((model) => (
                          <div
                            key={model.version_id}
                            className="rounded-2xl border border-white/10 bg-white/7 px-3 py-3"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="line-clamp-1 text-sm font-medium text-slate-100">
                                {model.name}
                              </p>
                              <span className="rounded-full bg-emerald-300/10 px-2.5 py-1 text-xs text-emerald-200">
                                {model.status}
                              </span>
                            </div>
                            <p className="mt-2 line-clamp-1 text-xs text-slate-500">
                              {model.base_model}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {!registryOverview ||
                    (registryOverview.datasets.length === 0 && registryOverview.models.length === 0) ? (
                      <p className="mt-4 rounded-2xl border border-white/10 bg-white/7 px-3 py-3 text-sm text-slate-400">
                        El registry aun no tiene versiones. Inicializalo para crear baseline.
                      </p>
                    ) : null}

                    {promotionDecision ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/7 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-slate-100">
                            Promotion Gate
                          </p>
                          <span
                            className={`rounded-full px-2.5 py-1 text-xs ${
                              promotionDecision.approved
                                ? "bg-emerald-300/10 text-emerald-200"
                                : "bg-amber-300/10 text-amber-200"
                            }`}
                          >
                            {promotionDecision.approved ? "approved" : "blocked"}
                          </span>
                        </div>
                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          {promotionDecision.checks.map((check) => (
                            <div
                              key={check.name}
                              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <p className="line-clamp-1 text-xs font-medium text-slate-200">
                                  {check.name}
                                </p>
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[11px] ${
                                    check.passed
                                      ? "bg-emerald-300/10 text-emerald-200"
                                      : "bg-red-300/10 text-red-200"
                                  }`}
                                >
                                  {check.passed ? "ok" : "fail"}
                                </span>
                              </div>
                              <p className="mt-1 line-clamp-1 text-xs text-slate-500">
                                {check.detail}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-[1.75rem] border border-white/12 bg-white/7 p-4 shadow-[0_30px_100px_rgba(0,0,0,0.28)] backdrop-blur-2xl">
                  <div className="flex items-center justify-between px-1 pb-3">
                    <div>
                      <h3 className="text-lg font-semibold">Chat con CEIBO IA</h3>
                      <p className="text-sm text-slate-400">
                        Conversacion directa con el CORE Orchestrator
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs ${
                        connectionState === "offline"
                          ? "bg-red-300/10 text-red-200"
                          : "bg-emerald-300/10 text-emerald-200"
                      }`}
                    >
                      {connectionState}
                    </span>
                  </div>

                  <div className="max-h-[300px] min-h-[260px] overflow-y-auto rounded-[1.25rem] border border-white/10 bg-black/25 p-4">
                    <div className="space-y-3">
                      {messages.map((message, index) => (
                        <div
                          key={`${message.role}-${index}`}
                          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`max-w-[86%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                              message.role === "user"
                                ? "bg-white text-slate-950"
                                : "border border-white/10 bg-white/8 text-slate-100"
                            }`}
                          >
                            {message.content}
                          </div>
                        </div>
                      ))}
                      {isSending ? (
                        <div className="w-fit rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-slate-300">
                          CEIBO procesando...
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {starterPrompts.map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => void sendMessage(prompt)}
                        className="rounded-full border border-white/10 bg-white/7 px-3 py-2 text-xs text-slate-300 transition hover:bg-white/12"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>

                  <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
                    <input
                      value={input}
                      onChange={(event) => setInput(event.target.value)}
                      placeholder="Escribe una orden para CEIBO CORE..."
                      className="min-w-0 flex-1 rounded-full border border-white/12 bg-white/8 px-5 py-3 text-sm text-white outline-none backdrop-blur placeholder:text-slate-500 focus:border-[#8be9ff]/60"
                    />
                    <button
                      type="submit"
                      disabled={isSending}
                      className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white text-slate-950 transition hover:bg-[#dff8ff] disabled:opacity-50"
                      aria-label="Enviar mensaje"
                    >
                      <Send className="h-5 w-5" />
                    </button>
                  </form>
                </div>

                <div className="hidden rounded-[1.5rem] border border-white/10 bg-[#080d18]/90 p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Agentes</h3>
                    <span className="rounded-full border border-white/10 bg-white/7 px-3 py-1 text-xs text-slate-300">
                      8 modules
                    </span>
                  </div>
                  <div className="mt-4 grid gap-2">
                    {agents.map((agent) => {
                      const Icon = agent.icon;
                      const isOnline = agent.status === "online";
                      return (
                        <div
                          key={agent.name}
                          className="group flex items-center justify-between rounded-2xl border border-white/8 bg-white/6 px-4 py-3 transition hover:border-[#8be9ff]/35 hover:bg-white/10"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-black/20">
                              <Icon className="h-5 w-5 text-[#8be9ff]" />
                            </div>
                            <div>
                              <p className="font-semibold">{agent.name}</p>
                              <p className="text-xs text-slate-500">{agent.signal}</p>
                            </div>
                          </div>
                          <span
                            className={`rounded-full px-3 py-1 text-xs ${
                              isOnline
                                ? "bg-emerald-300/10 text-emerald-200"
                                : "bg-amber-300/10 text-amber-200"
                            }`}
                          >
                            {agent.status}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="hidden rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Operations queue</p>
                      <h3 className="mt-1 text-lg font-semibold">Tareas de agentes</h3>
                    </div>
                    <button
                      onClick={() => void refreshOperations()}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/7 text-slate-300 transition hover:bg-white/12"
                      aria-label="Actualizar tareas"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </button>
                  </div>

                  <form onSubmit={createTask} className="mt-4 flex gap-2">
                    <input
                      value={taskGoal}
                      onChange={(event) => setTaskGoal(event.target.value)}
                      placeholder="Ej: revisar logs de Kubernetes"
                      className="min-w-0 flex-1 rounded-full border border-white/12 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#8be9ff]/60"
                    />
                    <button
                      type="submit"
                      disabled={isCreatingTask}
                      className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white text-slate-950 transition hover:bg-[#dff8ff] disabled:opacity-50"
                      aria-label="Crear tarea"
                    >
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </form>

                  <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          Orquestacion
                        </p>
                        <p className="mt-1 line-clamp-1 text-sm text-slate-300">
                          {orchestrationTraces[0]?.route_reason ?? "esperando task"}
                        </p>
                      </div>
                      <span className="rounded-full bg-[#8be9ff]/10 px-2.5 py-1 text-xs text-[#dff8ff]">
                        {orchestrationTraces[0]?.primary_agent.replace("_", " ") ?? "core"}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(orchestrationTraces[0]?.steps ?? []).slice(0, 4).map((step) => (
                        <span
                          key={`${step.agent}-${step.action}`}
                          className="rounded-full border border-white/10 bg-white/7 px-2.5 py-1 text-[11px] text-slate-300"
                        >
                          {step.action}: {step.agent.replace("_", " ")}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          Long-running Jobs
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          {longRunningJobs[0]?.current_step ?? "sin jobs activos"}
                        </p>
                      </div>
                      <span className="rounded-full bg-violet-300/10 px-2.5 py-1 text-xs text-violet-100">
                        {longRunningJobs.length} tracked
                      </span>
                    </div>
                    <div className="mt-3 space-y-2">
                      {longRunningJobs.slice(0, 3).map((job) => (
                        <div key={job.job_id}>
                          <div className="flex items-center justify-between gap-3 text-xs">
                            <span className="line-clamp-1 text-slate-300">{job.title}</span>
                            <span className="text-slate-500">{job.progress}%</span>
                          </div>
                          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full bg-violet-300 transition-all"
                              style={{ width: `${job.progress}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 space-y-2">
                    {tasks.length === 0 ? (
                      <p className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-400">
                        Todavia no hay tareas. Crea un objetivo para que CORE lo enrute.
                      </p>
                    ) : (
                      tasks.slice(0, 4).map((task) => (
                        <div
                          key={task.task_id}
                          className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="line-clamp-1 text-sm font-medium text-slate-100">
                              {task.goal}
                            </p>
                            <span className="rounded-full bg-emerald-300/10 px-2.5 py-1 text-xs text-emerald-200">
                              {task.status}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            {task.assigned_agent.replace("_", " ")} - priority {task.priority}
                          </p>
                        </div>
                      ))
                    )}
                  </div>

                  <p className="mt-4 line-clamp-2 text-xs leading-5 text-slate-500">
                    Ultima respuesta: {latestResponse}
                  </p>
                </div>

                <div className="hidden rounded-[1.5rem] border border-white/10 bg-[#07101b]/90 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm text-slate-400">Dataset trainer</p>
                      <h3 className="mt-1 text-lg font-semibold">Aprendizaje supervisado</h3>
                    </div>
                    <span className="rounded-full border border-[#8be9ff]/20 bg-[#8be9ff]/10 px-3 py-1 text-xs text-[#8be9ff]">
                      {trainingStats?.total_examples ?? 0} ejemplos
                    </span>
                  </div>

                  <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                      Ultimo intercambio
                    </p>
                    <p className="mt-2 line-clamp-2 text-sm text-slate-200">
                      {latestTrainingPair?.instruction ?? "Aun no hay conversacion para guardar."}
                    </p>
                  </div>

                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => void saveTrainingFeedback("good")}
                      disabled={!latestTrainingPair || isSavingTraining}
                      className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      Guardar buena
                    </button>
                    <button
                      type="button"
                      onClick={() => void saveTrainingFeedback("corrected")}
                      disabled={!latestTrainingPair || isSavingTraining}
                      className="rounded-full border border-[#8be9ff]/25 bg-[#8be9ff]/10 px-4 py-2 text-sm text-[#dff8ff] transition hover:bg-[#8be9ff]/15 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      Guardar correccion
                    </button>
                  </div>

                  <textarea
                    value={correction}
                    onChange={(event) => setCorrection(event.target.value)}
                    placeholder="Version corregida para entrenar a CEIBO..."
                    className="mt-3 min-h-[92px] w-full resize-none rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-slate-500 focus:border-[#8be9ff]/60"
                  />

                  {trainingNotice ? (
                    <p className="mt-2 text-xs text-slate-300">{trainingNotice}</p>
                  ) : null}

                  <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                          Curador
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          Limpieza, scoring y deduplicacion previa al fine-tuning.
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => void runDatasetCuration("preview")}
                        disabled={isCurating}
                        className="rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/12 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Analizar dataset
                      </button>
                      <button
                        type="button"
                        onClick={() => void runDatasetCuration("export")}
                        disabled={isCurating}
                        className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Exportar curado
                      </button>
                    </div>

                    {curationReport ? (
                      <div className="mt-4 space-y-3">
                        <div className="grid grid-cols-3 gap-2">
                          {[
                            ["Keep", curationReport.kept_examples],
                            ["Drop", curationReport.dropped_examples],
                            ["Score", curationReport.average_score],
                          ].map(([label, value]) => (
                            <div
                              key={label}
                              className="rounded-2xl border border-white/10 bg-white/7 px-3 py-2 text-center"
                            >
                              <p className="text-xs text-slate-500">{label}</p>
                              <p className="mt-1 text-lg font-semibold text-white">{value}</p>
                            </div>
                          ))}
                        </div>

                        {curationReport.output_path ? (
                          <p className="line-clamp-1 text-xs text-emerald-200">
                            Export: {curationReport.output_path}
                          </p>
                        ) : null}

                        <div className="space-y-2">
                          {curationReport.issues.slice(0, 3).map((issue) => (
                            <div
                              key={`${issue.code}-${issue.line_number}-${issue.example_id}`}
                              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <p className="line-clamp-1 text-xs font-medium text-slate-200">
                                  {issue.code}
                                </p>
                                <span className="rounded-full bg-white/8 px-2 py-0.5 text-[11px] text-slate-400">
                                  {issue.severity}
                                </span>
                              </div>
                              <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                                {issue.message}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                          Teacher IA
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          Ollama Mistral corrige y genera datos para CEIBO.
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs ${
                          teacherStatus?.available
                            ? "bg-emerald-300/10 text-emerald-200"
                            : "bg-red-300/10 text-red-200"
                        }`}
                      >
                        {teacherStatus?.available ? teacherStatus.model : "offline"}
                      </span>
                    </div>

                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => void runTeacherReview()}
                        disabled={!latestTrainingPair || !teacherStatus?.available || isTeacherRunning}
                        className="rounded-full border border-[#8be9ff]/25 bg-[#8be9ff]/10 px-4 py-2 text-sm text-[#dff8ff] transition hover:bg-[#8be9ff]/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Revisar respuesta
                      </button>
                      <button
                        type="button"
                        onClick={() => void generateTeacherExamples()}
                        disabled={!teacherStatus?.available || isTeacherRunning}
                        className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Generar ejemplos
                      </button>
                    </div>

                    <input
                      value={teacherTopic}
                      onChange={(event) => setTeacherTopic(event.target.value)}
                      placeholder="Tema para ejemplos sinteticos..."
                      className="mt-3 w-full rounded-full border border-white/12 bg-black/25 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#8be9ff]/60"
                    />

                    {teacherReview ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/7 px-4 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-white">
                            Score Mistral {teacherReview.score}/100
                          </p>
                          <span
                            className={`rounded-full px-2.5 py-1 text-xs ${
                              teacherReview.passed
                                ? "bg-emerald-300/10 text-emerald-200"
                                : "bg-amber-300/10 text-amber-200"
                            }`}
                          >
                            {teacherReview.passed ? "passed" : "review"}
                          </span>
                        </div>
                        <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">
                          {teacherReview.issues[0] ?? "Mistral aprobo esta respuesta."}
                        </p>
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                          QLoRA Runner
                        </p>
                        <p className="mt-1 text-sm text-slate-300">
                          Preflight y arranque del fine-tuning local.
                        </p>
                      </div>
                      <span className="rounded-full border border-white/10 bg-white/7 px-3 py-1 text-xs text-slate-300">
                        {trainingRun?.status ?? "idle"}
                      </span>
                    </div>

                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => void runQloraAction("preflight")}
                        disabled={isQloraRunning}
                        className="rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/12 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Preflight QLoRA
                      </button>
                      <button
                        type="button"
                        onClick={() => void runQloraAction("start")}
                        disabled={isQloraRunning}
                        className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Iniciar training
                      </button>
                    </div>

                    {trainingRun ? (
                      <div className="mt-4 space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <div className="rounded-2xl border border-white/10 bg-white/7 px-3 py-2">
                            <p className="text-xs text-slate-500">Dataset</p>
                            <p className="mt-1 text-lg font-semibold text-white">
                              {trainingRun.dataset_examples}
                            </p>
                          </div>
                          <div className="rounded-2xl border border-white/10 bg-white/7 px-3 py-2">
                            <p className="text-xs text-slate-500">Missing</p>
                            <p className="mt-1 text-lg font-semibold text-white">
                              {trainingRun.missing_requirements.length}
                            </p>
                          </div>
                        </div>
                        <p className="line-clamp-1 text-xs text-slate-400">
                          {trainingRun.base_model}
                        </p>
                        {trainingRun.missing_requirements.slice(0, 3).map((item) => (
                          <p key={item} className="text-xs text-amber-200">
                            {item}
                          </p>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-4 space-y-2">
                    {trainingExamples.length === 0 ? (
                      <p className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-400">
                        El dataset operativo todavia esta vacio.
                      </p>
                    ) : (
                      [...trainingExamples].reverse().map((example) => (
                        <div
                          key={example.example_id}
                          className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="line-clamp-1 text-sm font-medium text-slate-100">
                              {example.instruction}
                            </p>
                            <span className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-slate-300">
                              {example.rating ?? "manual"}
                            </span>
                          </div>
                          <p className="mt-1 line-clamp-1 text-xs text-slate-500">
                            {example.tags.slice(0, 3).join(" / ") || example.source}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}
