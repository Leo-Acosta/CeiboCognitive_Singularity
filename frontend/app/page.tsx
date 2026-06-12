"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  Code2,
  Copy,
  KeyRound,
  Loader2,
  Mic,
  MicOff,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  UserRound,
} from "lucide-react";

type SpeechRecognitionResultLike = {
  readonly isFinal: boolean;
  readonly [index: number]: { transcript: string };
};

type SpeechRecognitionEventLike = {
  readonly results: {
    readonly length: number;
    readonly [index: number]: SpeechRecognitionResultLike;
  };
};

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ChatResponse = {
  response: string;
  session_id: string;
  agent: string;
};

type LearningRating = "good" | "bad" | "corrected";

type LastExchange = {
  instruction: string;
  assistantResponse: string;
  intent: string | null;
  riskLevel: string | null;
  policyAction: string | null;
};

type LearningEventResponse = {
  saved: boolean;
  summary: string;
  next_actions: string[];
  example: {
    example_id: string;
    rating: LearningRating | null;
    tags: string[];
    source: string;
  };
};

type CoreStatus = {
  environment: string;
  agents_online: number;
  llm_provider: string;
  engine_model_id: string;
  engine_mode: string;
};

type VoiceStatusResponse = {
  enabled: boolean;
  authorized_users: string[];
  active_sessions: Record<string, string>;
  blocked_commands: number;
  mode: string;
  authorization_phrase_hint: string;
  safety_notes: string[];
};

type VoiceCommandResponse = {
  accepted: boolean;
  authorized: boolean;
  user_id: string;
  command: string | null;
  intent: string | null;
  risk_level: string | null;
  policy_action: string | null;
  cyber_category: string | null;
  reason: string;
  requires_authorization: boolean;
  requires_confirmation: boolean;
  double_confirmation_required: boolean;
  authorization_token: string | null;
  expires_at: string | null;
  safety_notes: string[];
};

type VoiceRevokeResponse = {
  revoked: boolean;
  user_id: string;
  message: string;
};

type CognitionSignal = {
  name: string;
  active: boolean;
  detail: string;
};

type CognitionLayer = {
  layer_id: string;
  name: string;
  purpose: string;
  score: number;
  status: string;
  signals: CognitionSignal[];
  next_actions: string[];
};

type CognitionState = {
  cognition_id: string;
  overall_score: number;
  maturity_level: string;
  summary: string;
  layers: CognitionLayer[];
  bottlenecks: string[];
  recommended_process: {
    order: number;
    name: string;
    description: string;
    required_layer: string;
  }[];
};

type DevCoreParameter = {
  name: string;
  value: string;
  confidence: number;
};

type DevCoreParseResponse = {
  intent: string;
  sub_intents: string[];
  confidence: number;
  risk_level: "low" | "medium" | "high" | "blocked";
  parameters: DevCoreParameter[];
  missing_parameters: string[];
  requires_confirmation: boolean;
  double_confirmation_required: boolean;
  cyber_category: string;
  policy_action: "allow" | "confirm" | "block";
  allowed_environment: string;
  safety_summary: string;
  recommended_action: string;
  structured_response: string;
};

type DevCoreTemplateIssue = {
  severity: string;
  code: string;
  message: string;
};

type DevCoreTemplateRenderResponse = {
  template_id: string;
  language: string;
  artifact_name: string;
  content: string;
  missing_parameters: string[];
  validation_issues: DevCoreTemplateIssue[];
  safe_to_execute: boolean;
  requires_review: boolean;
  safety_notes: string[];
};

type DevCoreExecutionResponse = {
  command: string;
  working_directory: string;
  status: "blocked" | "confirmation_required" | "completed" | "failed" | "timeout";
  exit_code: number | null;
  stdout: string;
  stderr: string;
  risk_level: string;
  cyber_category: string;
  policy_action: string;
  requires_confirmation: boolean;
  double_confirmation_required: boolean;
  validation_issues: DevCoreTemplateIssue[];
  audit_notes: string[];
};

type DevCorePatchPlanFile = {
  path: string;
  change_type: string;
  rationale: string;
};

type DevCorePatchChange = {
  path: string;
  change_type: string;
  content: string;
};

type DevCorePatchPlannerResponse = {
  patch_plan_id: string;
  goal: string;
  intent: string;
  risk_level: string;
  policy_action: string;
  cyber_category: string;
  requires_confirmation: boolean;
  files: DevCorePatchPlanFile[];
  steps: string[];
  suggested_tests: string[];
  diff_preview: string;
  validation_issues: DevCoreTemplateIssue[];
  applies_changes: boolean;
};

type DevCorePatchProposeResponse = {
  proposal_id: string;
  patch_plan_id: string;
  goal: string;
  proposed_changes: DevCorePatchChange[];
  diff_preview: string;
  suggested_tests: string[];
  validation_issues: DevCoreTemplateIssue[];
  applies_changes: boolean;
};

type DevCorePatchApplyResponse = {
  apply_id: string;
  patch_plan_id: string;
  status: "confirmation_required" | "blocked" | "no_changes" | "applied";
  risk_level: string;
  policy_action: string;
  cyber_category: string;
  requires_confirmation: boolean;
  applied_files: string[];
  snapshot_id: string | null;
  suggested_tests: string[];
  validation_issues: DevCoreTemplateIssue[];
  audit_notes: string[];
  applies_changes: boolean;
};

type DevCorePatchRollbackResponse = {
  rollback_id: string;
  snapshot_id: string;
  status: "confirmation_required" | "blocked" | "rolled_back";
  restored_files: string[];
  deleted_files: string[];
  validation_issues: DevCoreTemplateIssue[];
  audit_notes: string[];
  applies_changes: boolean;
};

type DevCorePatchVerifyResponse = {
  verification_id: string;
  command: string;
  status: "blocked" | "confirmation_required" | "completed" | "failed" | "timeout";
  exit_code: number | null;
  stdout: string;
  stderr: string;
  validation_issues: DevCoreTemplateIssue[];
  audit_notes: string[];
};

type WorkbenchHistoryItem = {
  id: string;
  kind: "parse" | "template" | "sandbox" | "patch" | "learning";
  title: string;
  detail: string;
};

const starterPrompts = [
  "Interpreta esta fase del proyecto y propone el siguiente paso.",
  "Crea POST /api/v1/tools en FastAPI con tests.",
  "Agrega un componente React llamado WorkbenchPanel.",
];

function newId() {
  return crypto.randomUUID();
}

function riskClasses(risk: DevCoreParseResponse["risk_level"]) {
  if (risk === "blocked") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (risk === "high") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  if (risk === "medium") {
    return "border-sky-200 bg-sky-50 text-sky-700";
  }
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function policyClasses(action: DevCoreParseResponse["policy_action"]) {
  if (action === "block") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (action === "confirm") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function executionStatusClasses(status: DevCoreExecutionResponse["status"]) {
  if (status === "blocked") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "failed" || status === "timeout") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-sky-200 bg-sky-50 text-sky-700";
}

function parameterValue(parse: DevCoreParseResponse, name: string) {
  return parse.parameters.find((parameter) => parameter.name === name)?.value;
}

function toIdentifier(value: string, fallback: string) {
  const cleaned = value
    .replace(/^\/+/, "")
    .split("/")
    .filter(Boolean)
    .pop()
    ?.replace(/[^a-zA-Z0-9_]/g, "_")
    .replace(/^(\d)/, "_$1")
    .toLowerCase();
  return cleaned || fallback;
}

function sandboxCommandForMessage(message: string, parse: DevCoreParseResponse) {
  if (parse.intent !== "execute_command") {
    return null;
  }
  const cleaned = message
    .trim()
    .replace(/^(ejecuta|corre|lanza|execute|run)\s+/i, "")
    .replace(/^(un|una)\s+/i, "")
    .replace(/^comando\s+/i, "")
    .trim();
  return cleaned || null;
}

function shouldPreparePatchPlan(parse: DevCoreParseResponse) {
  return (
    parse.policy_action !== "block" &&
    (parse.intent === "create_endpoint" || parse.intent === "modify_code")
  );
}

function templateRequestForParse(parse: DevCoreParseResponse) {
  if (parse.intent !== "create_endpoint" || parse.risk_level === "blocked") {
    return null;
  }

  const endpointPath = parameterValue(parse, "endpoint_path");
  const httpMethod = parameterValue(parse, "http_method")?.toLowerCase() ?? "post";
  if (!endpointPath) {
    return null;
  }

  const moduleName = toIdentifier(endpointPath, "generated_endpoint");
  return {
    template_id: "fastapi_endpoint",
    parameters: {
      module_name: moduleName,
      router_name: "router",
      http_method: httpMethod,
      endpoint_path: endpointPath,
      function_name: `${httpMethod}_${moduleName}`,
    },
  };
}

export default function Home() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: newId(),
      role: "assistant",
      content:
        "Estoy listo. Traeme una idea, un cambio de codigo o una decision tecnica y primero la interpreto con DevCore antes de actuar.",
    },
  ]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<CoreStatus | null>(null);
  const [cognitionState, setCognitionState] = useState<CognitionState | null>(null);
  const [parseResult, setParseResult] = useState<DevCoreParseResponse | null>(null);
  const [templatePreview, setTemplatePreview] = useState<DevCoreTemplateRenderResponse | null>(null);
  const [executionPreview, setExecutionPreview] = useState<DevCoreExecutionResponse | null>(null);
  const [patchPreview, setPatchPreview] = useState<DevCorePatchPlannerResponse | null>(null);
  const [patchProposal, setPatchProposal] = useState<DevCorePatchProposeResponse | null>(null);
  const [patchApplyPreview, setPatchApplyPreview] = useState<DevCorePatchApplyResponse | null>(null);
  const [patchRollbackPreview, setPatchRollbackPreview] = useState<DevCorePatchRollbackResponse | null>(null);
  const [patchVerifyPreview, setPatchVerifyPreview] = useState<DevCorePatchVerifyResponse | null>(null);
  const [workbenchHistory, setWorkbenchHistory] = useState<WorkbenchHistoryItem[]>([]);
  const [lastExchange, setLastExchange] = useState<LastExchange | null>(null);
  const [learningCorrection, setLearningCorrection] = useState("");
  const [learningMessage, setLearningMessage] = useState("Todavia no guardaste feedback.");
  const [isSending, setIsSending] = useState(false);
  const [isSavingLearning, setIsSavingLearning] = useState(false);
  const [isRenderingTemplate, setIsRenderingTemplate] = useState(false);
  const [isPreparingExecution, setIsPreparingExecution] = useState(false);
  const [isPlanningPatch, setIsPlanningPatch] = useState(false);
  const [isProposingPatch, setIsProposingPatch] = useState(false);
  const [isCheckingPatchGate, setIsCheckingPatchGate] = useState(false);
  const [isRollingBackPatch, setIsRollingBackPatch] = useState(false);
  const [isVerifyingPatch, setIsVerifyingPatch] = useState(false);
  const [isConfirmingExecution, setIsConfirmingExecution] = useState(false);
  const [connection, setConnection] = useState<"ready" | "offline">("ready");
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatusResponse | null>(null);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceAuthorized, setVoiceAuthorized] = useState(false);
  const [voiceToken, setVoiceToken] = useState<string | null>(null);
  const [voiceExpiresAt, setVoiceExpiresAt] = useState<string | null>(null);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceMessage, setVoiceMessage] = useState("Deci: CEIBO autoriza mi voz.");
  const [lastVoiceDecision, setLastVoiceDecision] = useState<VoiceCommandResponse | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const statusLabel = useMemo(() => {
    if (connection === "offline") {
      return "offline";
    }
    return status?.engine_mode ?? "ready";
  }, [connection, status]);

  useEffect(() => {
    void refreshStatus();
    setVoiceSupported(Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
    void refreshVoiceStatus();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function refreshStatus() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/status`);
      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }
      setStatus((await response.json()) as CoreStatus);
      void refreshCognition();
      setConnection("ready");
    } catch {
      setConnection("offline");
    }
  }

  async function refreshCognition() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/cognition/state`);
      if (!response.ok) {
        throw new Error(`Cognition responded ${response.status}`);
      }
      setCognitionState((await response.json()) as CognitionState);
    } catch {
      setCognitionState(null);
    }
  }

  async function refreshVoiceStatus() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/voice/status`);
      if (!response.ok) {
        throw new Error(`Voice responded ${response.status}`);
      }
      const data = (await response.json()) as VoiceStatusResponse;
      setVoiceStatus(data);
      const activeOwnerSession = data.active_sessions["local-owner"];
      if (activeOwnerSession && voiceToken) {
        setVoiceAuthorized(true);
        setVoiceExpiresAt(activeOwnerSession);
      }
      if (!voiceAuthorized) {
        setVoiceMessage(data.authorization_phrase_hint);
      }
    } catch {
      setVoiceStatus(null);
    }
  }

  async function parseMessage(content: string) {
    const response = await fetch(`${apiUrl}/api/v1/devcore/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: content }),
    });
    if (!response.ok) {
      throw new Error(`Parser responded ${response.status}`);
    }
    return (await response.json()) as DevCoreParseResponse;
  }

  async function renderTemplateForParse(parse: DevCoreParseResponse) {
    const request = templateRequestForParse(parse);
    if (!request) {
      setTemplatePreview(null);
      return;
    }

    setIsRenderingTemplate(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/templates/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      if (!response.ok) {
        throw new Error(`Template engine responded ${response.status}`);
      }
      const rendered = (await response.json()) as DevCoreTemplateRenderResponse;
      setTemplatePreview(rendered);
      addHistory({
        kind: "template",
        title: rendered.artifact_name,
        detail: `${rendered.template_id} - ${rendered.language}`,
      });
    } catch {
      setTemplatePreview(null);
    } finally {
      setIsRenderingTemplate(false);
    }
  }

  async function prepareExecutionForParse(content: string, parse: DevCoreParseResponse) {
    const command = sandboxCommandForMessage(content, parse);
    if (!command) {
      setExecutionPreview(null);
      return;
    }

    setIsPreparingExecution(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      if (!response.ok) {
        throw new Error(`Execution sandbox responded ${response.status}`);
      }
      const prepared = (await response.json()) as DevCoreExecutionResponse;
      setExecutionPreview(prepared);
      addHistory({
        kind: "sandbox",
        title: prepared.status,
        detail: prepared.command,
      });
    } catch {
      setExecutionPreview(null);
    } finally {
      setIsPreparingExecution(false);
    }
  }

  async function confirmSandboxExecution() {
    if (!executionPreview || isConfirmingExecution) {
      return;
    }
    setIsConfirmingExecution(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command: executionPreview.command,
          confirmation_phrase: "CONFIRM_EXECUTION",
        }),
      });
      if (!response.ok) {
        throw new Error(`Execution sandbox responded ${response.status}`);
      }
      const executed = (await response.json()) as DevCoreExecutionResponse;
      setExecutionPreview(executed);
      addHistory({
        kind: "sandbox",
        title: executed.status,
        detail: `${executed.command}${executed.exit_code === null ? "" : ` - exit ${executed.exit_code}`}`,
      });
    } finally {
      setIsConfirmingExecution(false);
    }
  }

  async function preparePatchPlan(content: string, parse: DevCoreParseResponse) {
    if (!shouldPreparePatchPlan(parse)) {
      setPatchPreview(null);
      setPatchProposal(null);
      setPatchApplyPreview(null);
      setPatchRollbackPreview(null);
      setPatchVerifyPreview(null);
      return;
    }

    setIsPlanningPatch(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/patch-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: content }),
      });
      if (!response.ok) {
        throw new Error(`Patch planner responded ${response.status}`);
      }
      const planned = (await response.json()) as DevCorePatchPlannerResponse;
      setPatchPreview(planned);
      setPatchProposal(null);
      setPatchApplyPreview(null);
      setPatchRollbackPreview(null);
      setPatchVerifyPreview(null);
      addHistory({
        kind: "patch",
        title: planned.intent,
        detail: `${planned.files.length} archivos - ${planned.suggested_tests.length} tests`,
      });
      await proposePatchChanges(planned);
    } catch {
      setPatchPreview(null);
      setPatchProposal(null);
      setPatchApplyPreview(null);
      setPatchRollbackPreview(null);
      setPatchVerifyPreview(null);
    } finally {
      setIsPlanningPatch(false);
    }
  }

  async function proposePatchChanges(plan = patchPreview) {
    if (!plan || isProposingPatch) {
      return;
    }

    setIsProposingPatch(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/patch-propose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patch_plan_id: plan.patch_plan_id,
          goal: plan.goal,
          files: plan.files,
        }),
      });
      if (!response.ok) {
        throw new Error(`Patch proposer responded ${response.status}`);
      }
      const proposal = (await response.json()) as DevCorePatchProposeResponse;
      setPatchProposal(proposal);
      setPatchApplyPreview(null);
      setPatchRollbackPreview(null);
      setPatchVerifyPreview(null);
      addHistory({
        kind: "patch",
        title: "proposal ready",
        detail: `${proposal.proposed_changes.length} cambios propuestos`,
      });
    } catch {
      setPatchProposal(null);
    } finally {
      setIsProposingPatch(false);
    }
  }

  async function checkPatchApplyGate(applyConfirmed = false) {
    if (!patchPreview || isCheckingPatchGate) {
      return;
    }

    setIsCheckingPatchGate(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/patch-apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patch_plan_id: patchPreview.patch_plan_id,
          goal: patchPreview.goal,
          files: patchPreview.files,
          proposed_changes: patchProposal?.proposed_changes ?? [],
          confirmation_phrase: applyConfirmed ? "APPLY_PATCH" : undefined,
        }),
      });
      if (!response.ok) {
        throw new Error(`Patch apply gate responded ${response.status}`);
      }
      const checked = (await response.json()) as DevCorePatchApplyResponse;
      setPatchApplyPreview(checked);
      setPatchRollbackPreview(null);
      setPatchVerifyPreview(null);
      addHistory({
        kind: "patch",
        title: `gate ${checked.status}`,
        detail: checked.applies_changes ? checked.applied_files.join(", ") : "sin aplicar cambios",
      });
    } catch {
      setPatchApplyPreview(null);
    } finally {
      setIsCheckingPatchGate(false);
    }
  }

  async function verifyAppliedPatch() {
    const command = patchApplyPreview?.suggested_tests[0];
    if (!command || isVerifyingPatch) {
      return;
    }

    setIsVerifyingPatch(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/patch-verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      if (!response.ok) {
        throw new Error(`Patch verify responded ${response.status}`);
      }
      const verified = (await response.json()) as DevCorePatchVerifyResponse;
      setPatchVerifyPreview(verified);
      addHistory({
        kind: "patch",
        title: `verify ${verified.status}`,
        detail: verified.command,
      });
    } catch {
      setPatchVerifyPreview(null);
    } finally {
      setIsVerifyingPatch(false);
    }
  }

  async function rollbackAppliedPatch() {
    if (!patchApplyPreview?.snapshot_id || isRollingBackPatch) {
      return;
    }

    setIsRollingBackPatch(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/devcore/patch-rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          snapshot_id: patchApplyPreview.snapshot_id,
          confirmation_phrase: "ROLLBACK_PATCH",
        }),
      });
      if (!response.ok) {
        throw new Error(`Patch rollback responded ${response.status}`);
      }
      const rollback = (await response.json()) as DevCorePatchRollbackResponse;
      setPatchRollbackPreview(rollback);
      addHistory({
        kind: "patch",
        title: `rollback ${rollback.status}`,
        detail: [...rollback.restored_files, ...rollback.deleted_files].join(", ") || "sin archivos",
      });
    } catch {
      setPatchRollbackPreview(null);
    } finally {
      setIsRollingBackPatch(false);
    }
  }

  function addHistory(item: Omit<WorkbenchHistoryItem, "id">) {
    setWorkbenchHistory((current) => [{ id: newId(), ...item }, ...current].slice(0, 5));
  }

  function startVoiceListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition || voiceListening) {
      setVoiceMessage("Este navegador no tiene reconocimiento de voz disponible.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "es-AR";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcripts: string[] = [];
      for (let index = 0; index < event.results.length; index += 1) {
        transcripts.push(event.results[index][0].transcript);
      }
      const transcript = transcripts.join(" ").trim();
      setVoiceTranscript(transcript);
      void handleVoiceCommand(transcript);
    };
    recognition.onerror = () => {
      setVoiceListening(false);
      setVoiceMessage("No pude escuchar bien. Revisa permisos de microfono y proba otra vez.");
    };
    recognition.onend = () => {
      setVoiceListening(false);
    };
    recognitionRef.current = recognition;
    setVoiceListening(true);
    setVoiceMessage(voiceAuthorized ? "Te escucho. Dicta una orden." : "Deci: CEIBO autoriza mi voz.");
    recognition.start();
  }

  function stopVoiceListening() {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setVoiceListening(false);
  }

  async function handleVoiceCommand(transcript: string) {
    if (!transcript.trim()) {
      setVoiceMessage("No detecte texto en la voz.");
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/api/v1/voice/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript,
          user_id: "local-owner",
          session_id: sessionId,
          authorization_token: voiceToken,
        }),
      });
      if (!response.ok) {
        throw new Error(`Voice command responded ${response.status}`);
      }
      const data = (await response.json()) as VoiceCommandResponse;
      setVoiceAuthorized(data.authorized);
      setVoiceToken(data.authorization_token ?? voiceToken);
      setVoiceExpiresAt(data.expires_at ?? voiceExpiresAt);
      setVoiceMessage(data.reason);
      setLastVoiceDecision(data);
      addHistory({
        kind: "parse",
        title: data.intent ? `voice ${data.intent}` : data.accepted ? "voice command" : "voice auth",
        detail: data.command ?? data.reason,
      });

      if (data.accepted && data.command) {
        await sendMessage(data.command);
      }
    } catch {
      setVoiceMessage("No pude validar la voz con la API local.");
      setConnection("offline");
    }
  }

  async function revokeVoiceSession() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/voice/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "local-owner",
          authorization_token: voiceToken,
        }),
      });
      if (!response.ok) {
        throw new Error(`Voice revoke responded ${response.status}`);
      }
      const data = (await response.json()) as VoiceRevokeResponse;
      setVoiceAuthorized(false);
      setVoiceToken(null);
      setVoiceExpiresAt(null);
      setVoiceMessage(data.message);
      setLastVoiceDecision(null);
      void refreshVoiceStatus();
    } catch {
      setVoiceMessage("No pude bloquear la voz desde la API local.");
    }
  }

  async function saveLearningEvent(rating: LearningRating) {
    if (!lastExchange || isSavingLearning) {
      return;
    }
    const correction = learningCorrection.trim();
    if (rating === "corrected" && !correction) {
      setLearningMessage("Escribi una correccion ideal antes de guardar.");
      return;
    }

    setIsSavingLearning(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/engine/training/learning-event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: lastExchange.instruction,
          assistant_response: lastExchange.assistantResponse,
          rating,
          corrected_response: correction || null,
          source: "workbench",
          tags: ["chat", "human-feedback"],
          metadata: {
            surface: "devcore-workbench",
            intent: lastExchange.intent,
            risk_level: lastExchange.riskLevel,
            policy_action: lastExchange.policyAction,
          },
        }),
      });
      if (!response.ok) {
        throw new Error(`Learning event responded ${response.status}`);
      }
      const data = (await response.json()) as LearningEventResponse;
      setLearningMessage(data.summary);
      setLearningCorrection("");
      addHistory({
        kind: "learning",
        title: `feedback ${data.example.rating ?? rating}`,
        detail: data.summary,
      });
      void refreshCognition();
    } catch {
      setLearningMessage("No pude guardar el feedback en el dataset local.");
      setConnection("offline");
    } finally {
      setIsSavingLearning(false);
    }
  }

  async function sendMessage(nextMessage?: string) {
    const content = (nextMessage ?? input).trim();
    if (!content || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);
    setMessages((current) => [...current, { id: newId(), role: "user", content }]);

    try {
      const parsed = await parseMessage(content);
      setParseResult(parsed);
      addHistory({
        kind: "parse",
        title: parsed.intent,
        detail: `${parsed.policy_action} - ${parsed.cyber_category}`,
      });
      await renderTemplateForParse(parsed);
      await prepareExecutionForParse(content, parsed);
      await preparePatchPlan(content, parsed);

      const response = await fetch(`${apiUrl}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          metadata: {
            surface: "focused-chat",
            devcore_parse: parsed,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`API responded ${response.status}`);
      }

      const data = (await response.json()) as ChatResponse;
      setSessionId(data.session_id);
      setMessages((current) => [
        ...current,
        { id: newId(), role: "assistant", content: data.response },
      ]);
      setLastExchange({
        instruction: content,
        assistantResponse: data.response,
        intent: parsed.intent,
        riskLevel: parsed.risk_level,
        policyAction: parsed.policy_action,
      });
      setLearningMessage("Respuesta lista para feedback humano.");
      setConnection("ready");
      void refreshStatus();
    } catch {
      setConnection("offline");
      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content:
            "No pude completar la solicitud con la API local. Revisa Docker y vuelve a intentar cuando el backend este disponible.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage();
  }

  function resetChat() {
      setSessionId(null);
      setParseResult(null);
      setTemplatePreview(null);
      setExecutionPreview(null);
      setPatchPreview(null);
      setPatchProposal(null);
      setPatchApplyPreview(null);
      setPatchRollbackPreview(null);
      setPatchVerifyPreview(null);
      setWorkbenchHistory([]);
      setLastExchange(null);
      setLearningCorrection("");
      setLearningMessage("Todavia no guardaste feedback.");
      setMessages([
      {
        id: newId(),
        role: "assistant",
        content: "Nueva conversacion lista. Decime que queres construir, revisar o decidir.",
      },
    ]);
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[#eef3f8] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 pb-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-white shadow-lg shadow-slate-300">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">
                CEIBO CORE
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal text-slate-950">
                DevCore Workbench
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`hidden items-center gap-2 rounded-full border px-3 py-2 text-sm sm:inline-flex ${
                voiceAuthorized
                  ? "border-emerald-200 bg-white text-emerald-700"
                  : "border-slate-200 bg-white text-slate-600"
              }`}
            >
              <KeyRound className="h-4 w-4" />
              {voiceAuthorized ? "voz autorizada" : "voz bloqueada"}
            </span>
            <button
              type="button"
              onClick={voiceListening ? stopVoiceListening : startVoiceListening}
              disabled={!voiceSupported || isSending}
              className={`inline-flex h-10 w-10 items-center justify-center rounded-full border shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
                voiceListening
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-slate-200 bg-white text-slate-600 hover:border-sky-300 hover:text-sky-900"
              }`}
              aria-label={voiceListening ? "Detener escucha" : "Escuchar por voz"}
              title={voiceListening ? "Detener escucha" : "Escuchar por voz"}
            >
              {voiceListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </button>
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm ${
                connection === "ready"
                  ? "border-emerald-200 bg-white text-emerald-700"
                  : "border-red-200 bg-white text-red-700"
              }`}
            >
              <CheckCircle2 className="h-4 w-4" />
              {statusLabel}
            </span>
            <button
              type="button"
              onClick={resetChat}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-950"
              aria-label="Reiniciar chat"
              title="Reiniciar chat"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>
        </header>

        <section className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="grid min-h-0 grid-rows-[1fr_auto] overflow-hidden rounded-lg border border-white bg-white/80 shadow-[0_24px_80px_rgba(15,23,42,0.12)] backdrop-blur">
            <div className="min-h-0 overflow-y-auto px-4 py-5 sm:px-6">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
                {messages.map((message) => {
                  const isUser = message.role === "user";
                  return (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {!isUser ? (
                        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-950 text-white">
                          <Bot className="h-4 w-4" />
                        </div>
                      ) : null}
                      <div
                        className={`max-w-[84%] whitespace-pre-wrap rounded-lg px-4 py-3 text-sm leading-6 shadow-sm sm:text-base ${
                          isUser
                            ? "bg-sky-900 text-white shadow-sky-100"
                            : "border border-slate-200 bg-white text-slate-800"
                        }`}
                      >
                        {message.content}
                      </div>
                      {isUser ? (
                        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                          <UserRound className="h-4 w-4" />
                        </div>
                      ) : null}
                    </div>
                  );
                })}

                {isSending ? (
                  <div className="flex items-center gap-3 text-sm text-slate-500">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-white">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                    Interpretando y respondiendo...
                  </div>
                ) : null}
                <div ref={scrollRef} />
              </div>
            </div>

            <div className="border-t border-slate-200 bg-white/90 px-4 py-4 sm:px-6">
              <div className="mx-auto w-full max-w-3xl">
                <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                  {starterPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void sendMessage(prompt)}
                      disabled={isSending}
                      className="shrink-0 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 transition hover:border-sky-300 hover:bg-white hover:text-sky-900 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>

                <form
                  onSubmit={handleSubmit}
                  className="flex items-end gap-2 rounded-lg border border-slate-200 bg-white p-2 shadow-sm"
                >
                  <textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        void sendMessage();
                      }
                    }}
                    placeholder="Escribi una instruccion para CEIBO..."
                    rows={1}
                    className="max-h-36 min-h-11 flex-1 resize-none rounded-md border-0 bg-transparent px-3 py-3 text-base leading-6 text-slate-950 outline-none placeholder:text-slate-400"
                  />
                  <button
                    type="button"
                    onClick={() => void sendMessage()}
                    disabled={!input.trim() || isSending}
                    className="hidden h-11 shrink-0 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 transition hover:border-sky-300 hover:bg-white hover:text-sky-900 disabled:cursor-not-allowed disabled:opacity-50 sm:inline-flex"
                    title="Preparar patch plan"
                  >
                    <Code2 className="h-4 w-4" />
                    Patch plan
                  </button>
                  <button
                    type="submit"
                    disabled={!input.trim() || isSending}
                    className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-slate-950 text-white transition hover:bg-sky-900 disabled:cursor-not-allowed disabled:bg-slate-300"
                    aria-label="Enviar mensaje"
                    title="Enviar mensaje"
                  >
                    {isSending ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Send className="h-5 w-5" />
                    )}
                  </button>
                </form>
              </div>
            </div>
          </div>

          <aside className="min-h-0 overflow-y-auto rounded-lg border border-white bg-white/70 p-5 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
            <div className="mb-5 rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Voice Control v1
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-slate-950">
                    Ordenes por voz
                  </h2>
                </div>
                {voiceAuthorized ? (
                  <Mic className="h-5 w-5 text-emerald-700" />
                ) : (
                  <MicOff className="h-5 w-5 text-slate-500" />
                )}
              </div>

              <div className="mt-4 space-y-3">
                <div
                  className={`rounded-md border px-3 py-2 text-sm ${
                    voiceAuthorized
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-slate-200 bg-slate-50 text-slate-600"
                  }`}
                >
                  <p className="font-semibold">
                    {voiceAuthorized ? "Dueno autorizado" : "Esperando autorizacion"}
                  </p>
                  <p className="mt-1 text-xs leading-5">{voiceMessage}</p>
                </div>

                {voiceTranscript ? (
                  <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Ultima escucha
                    </p>
                    <p className="mt-1 text-sm leading-5 text-slate-700">{voiceTranscript}</p>
                  </div>
                ) : null}

                {lastVoiceDecision?.intent ? (
                  <div
                    className={`rounded-md border px-3 py-2 text-sm ${
                      lastVoiceDecision.policy_action === "block"
                        ? "border-red-200 bg-red-50 text-red-700"
                        : lastVoiceDecision.requires_confirmation
                          ? "border-amber-200 bg-amber-50 text-amber-700"
                          : "border-emerald-200 bg-emerald-50 text-emerald-700"
                    }`}
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.16em]">
                      Voice safety
                    </p>
                    <p className="mt-1 font-semibold">{lastVoiceDecision.intent}</p>
                    <p className="mt-1 text-xs leading-5">
                      {lastVoiceDecision.risk_level} - {lastVoiceDecision.policy_action}
                      {lastVoiceDecision.cyber_category
                        ? ` - ${lastVoiceDecision.cyber_category}`
                        : ""}
                    </p>
                    {lastVoiceDecision.double_confirmation_required ? (
                      <p className="mt-2 rounded-full bg-white/70 px-2.5 py-1 text-xs font-medium">
                        doble confirmacion requerida
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {(voiceExpiresAt || voiceStatus) ? (
                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Expira
                      </p>
                      <p className="mt-1 text-xs leading-5 text-slate-700">
                        {voiceExpiresAt
                          ? new Date(voiceExpiresAt).toLocaleTimeString()
                          : "sin sesion"}
                      </p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Bloqueos
                      </p>
                      <p className="mt-1 text-xs leading-5 text-slate-700">
                        {voiceStatus?.blocked_commands ?? 0}
                      </p>
                    </div>
                  </div>
                ) : null}

                <button
                  type="button"
                  onClick={voiceListening ? stopVoiceListening : startVoiceListening}
                  disabled={!voiceSupported || isSending}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-medium text-white transition hover:bg-sky-900 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {voiceListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                  {voiceListening ? "Detener escucha" : "Hablar con CEIBO"}
                </button>

                {voiceAuthorized ? (
                  <button
                    type="button"
                    onClick={() => void revokeVoiceSession()}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700"
                  >
                    <KeyRound className="h-4 w-4" />
                    Bloquear voz
                  </button>
                ) : null}

                {!voiceSupported ? (
                  <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                    Tu navegador actual no expone Web Speech API. Proba desde Chrome o Edge.
                  </p>
                ) : null}

                <p className="text-xs leading-5 text-slate-500">
                  {voiceStatus?.safety_notes[0] ??
                    "Voice v1 autoriza por frase hablada; las ordenes siguen pasando por seguridad."}
                </p>
              </div>
            </div>

            <div className="mb-5 rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Cognition v1
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-slate-950">
                    Capas de inteligencia
                  </h2>
                </div>
                <Sparkles className="h-5 w-5 text-sky-700" />
              </div>

              {cognitionState ? (
                <div className="mt-4 space-y-4">
                  <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-slate-800">
                        {cognitionState.maturity_level}
                      </p>
                      <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700">
                        {cognitionState.overall_score}/100
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      {cognitionState.summary}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {cognitionState.layers.map((layer) => (
                      <div
                        key={layer.layer_id}
                        className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
                      >
                        <p className="truncate text-xs font-semibold text-slate-700">
                          {layer.name}
                        </p>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
                          <div
                            className="h-full rounded-full bg-sky-700"
                            style={{ width: `${layer.score}%` }}
                          />
                        </div>
                        <p className="mt-1 text-xs text-slate-500">{layer.score}/100</p>
                      </div>
                    ))}
                  </div>

                  {cognitionState.bottlenecks.length ? (
                    <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
                        Cuellos de botella
                      </p>
                      <p className="mt-1 text-xs leading-5 text-amber-800">
                        {cognitionState.bottlenecks.join(" | ")}
                      </p>
                    </div>
                  ) : null}

                  <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Proceso
                    </p>
                    <p className="mt-1 text-xs leading-5 text-slate-600">
                      {cognitionState.recommended_process
                        .slice(0, 4)
                        .map((step) => step.name)
                        .join(" -> ")}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-500">
                  La capa cognitiva aparece cuando la API local responde.
                </p>
              )}
            </div>

            <div className="mb-5 rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Sprint 31
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-slate-950">
                    Learning Loop v1
                  </h2>
                </div>
                <CheckCircle2 className="h-5 w-5 text-emerald-700" />
              </div>

              {lastExchange ? (
                <div className="mt-4 space-y-3">
                  <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Ultima respuesta
                    </p>
                    <p className="mt-1 line-clamp-3 text-sm leading-6 text-slate-700">
                      {lastExchange.assistantResponse}
                    </p>
                  </div>

                  <textarea
                    value={learningCorrection}
                    onChange={(event) => setLearningCorrection(event.target.value)}
                    placeholder="Correccion ideal opcional..."
                    className="min-h-24 w-full resize-none rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-sky-400 focus:bg-white"
                  />

                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => void saveLearningEvent("good")}
                      disabled={isSavingLearning}
                      className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-2 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Buena
                    </button>
                    <button
                      type="button"
                      onClick={() => void saveLearningEvent("bad")}
                      disabled={isSavingLearning}
                      className="rounded-md border border-red-200 bg-red-50 px-2 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Mala
                    </button>
                    <button
                      type="button"
                      onClick={() => void saveLearningEvent("corrected")}
                      disabled={isSavingLearning}
                      className="rounded-md border border-sky-200 bg-sky-50 px-2 py-2 text-xs font-semibold text-sky-700 transition hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Corregir
                    </button>
                  </div>

                  <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">
                    {isSavingLearning ? "Guardando feedback..." : learningMessage}
                  </p>
                </div>
              ) : (
                <p className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-500">
                  Cuando CEIBO responda, vas a poder marcar la salida como buena, mala o
                  corregida para alimentar el dataset local.
                </p>
              )}
            </div>

            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Sprint 17
                </p>
                <h2 className="mt-1 text-lg font-semibold text-slate-950">
                  Interpretacion
                </h2>
              </div>
              <ShieldCheck className="h-5 w-5 text-sky-700" />
            </div>

            {parseResult ? (
              <div className="mt-5 space-y-4">
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">Intencion</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">{parseResult.intent}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    Confianza {Math.round(parseResult.confidence * 100)}%
                  </p>
                  {parseResult.sub_intents.length ? (
                    <p className="mt-2 text-xs text-slate-500">
                      Tambien detecta: {parseResult.sub_intents.join(", ")}
                    </p>
                  ) : null}
                </div>

                <div className={`rounded-lg border p-4 ${riskClasses(parseResult.risk_level)}`}>
                  <p className="text-xs uppercase tracking-[0.16em]">Riesgo</p>
                  <p className="mt-1 text-base font-semibold">{parseResult.risk_level}</p>
                  <p className="mt-1 text-sm">
                    {parseResult.requires_confirmation
                      ? "Requiere confirmacion antes de avanzar."
                      : "Puede continuar en modo seguro."}
                  </p>
                </div>

                <div className={`rounded-lg border p-4 ${policyClasses(parseResult.policy_action)}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em]">Sprint 19</p>
                      <p className="mt-1 text-base font-semibold">
                        {parseResult.policy_action}
                      </p>
                    </div>
                    {parseResult.policy_action === "block" ? (
                      <ShieldAlert className="h-5 w-5 shrink-0" />
                    ) : (
                      <ShieldCheck className="h-5 w-5 shrink-0" />
                    )}
                  </div>
                  <p className="mt-2 text-sm">
                    {parseResult.cyber_category} - {parseResult.allowed_environment}
                  </p>
                  <p className="mt-2 text-sm leading-6">{parseResult.safety_summary}</p>
                  {parseResult.double_confirmation_required ? (
                    <p className="mt-2 inline-flex rounded-full bg-white/70 px-2.5 py-1 text-xs font-medium">
                      doble confirmacion requerida
                    </p>
                  ) : null}
                </div>

                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">Accion recomendada</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {parseResult.recommended_action}
                  </p>
                </div>

                {parseResult.missing_parameters.length ? (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
                      Faltantes
                    </p>
                    <p className="mt-2 text-sm leading-6 text-amber-800">
                      {parseResult.missing_parameters.join(", ")}
                    </p>
                  </div>
                ) : null}

                <div className="space-y-2">
                  {parseResult.parameters.length ? (
                    parseResult.parameters.map((parameter) => (
                      <div
                        key={`${parameter.name}-${parameter.value}`}
                        className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                      >
                        <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-sky-700" />
                        <div>
                          <p className="font-medium text-slate-800">{parameter.name}</p>
                          <p className="text-slate-500">{parameter.value}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
                      Sin parametros especificos todavia.
                    </p>
                  )}
                </div>

                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Sprint 20
                      </p>
                      <h3 className="mt-1 text-base font-semibold text-slate-950">
                        Sandbox
                      </h3>
                    </div>
                    <Terminal className="h-5 w-5 text-sky-700" />
                  </div>

                  {isPreparingExecution ? (
                    <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Preparando sandbox...
                    </div>
                  ) : executionPreview ? (
                    <div className="mt-4 space-y-3">
                      <div className={`rounded-md border px-3 py-2 text-sm ${executionStatusClasses(executionPreview.status)}`}>
                        <p className="font-semibold">{executionPreview.status}</p>
                        <p className="mt-1 text-xs">
                          {executionPreview.cyber_category} - {executionPreview.policy_action}
                        </p>
                      </div>
                      <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                        <p className="text-xs text-slate-500">Comando</p>
                        <code className="mt-1 block break-all text-sm text-slate-800">
                          {executionPreview.command}
                        </code>
                      </div>
                      {executionPreview.validation_issues.length ? (
                        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                          {executionPreview.validation_issues[0].message}
                        </div>
                      ) : null}
                      {executionPreview.status === "confirmation_required" &&
                      !executionPreview.double_confirmation_required ? (
                        <button
                          type="button"
                          onClick={() => void confirmSandboxExecution()}
                          disabled={isConfirmingExecution}
                          className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-medium text-white transition hover:bg-sky-900 disabled:cursor-not-allowed disabled:bg-slate-300"
                        >
                          {isConfirmingExecution ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Terminal className="h-4 w-4" />
                          )}
                          Ejecutar con confirmacion
                        </button>
                      ) : null}
                      {executionPreview.double_confirmation_required ? (
                        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs leading-5 text-red-700">
                          Esta accion requiere doble confirmacion y no se ejecuta desde este panel.
                        </div>
                      ) : null}
                      {executionPreview.stdout || executionPreview.stderr ? (
                        <pre className="max-h-52 overflow-auto rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                          <code>{executionPreview.stdout || executionPreview.stderr}</code>
                        </pre>
                      ) : null}
                      <p className="text-xs leading-5 text-slate-500">
                        La ejecucion real exige confirmacion explicita y queda auditada.
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-500">
                      Aparece cuando la intencion sea ejecutar un comando.
                    </p>
                  )}
                </div>

                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Sprint 23
                      </p>
                      <h3 className="mt-1 text-base font-semibold text-slate-950">
                        Patch preview
                      </h3>
                    </div>
                    <AlertTriangle className="h-5 w-5 text-sky-700" />
                  </div>

                  {isPlanningPatch ? (
                    <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Preparando patch plan...
                    </div>
                  ) : patchPreview ? (
                    <div className="mt-4 space-y-4">
                      <div className="flex flex-wrap gap-2">
                        <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">
                          {patchPreview.intent}
                        </span>
                        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                          preview only
                        </span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          {patchPreview.policy_action}
                        </span>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                          Archivos objetivo
                        </p>
                        <div className="mt-2 space-y-2">
                          {patchPreview.files.map((file) => (
                            <div
                              key={`${file.path}-${file.change_type}`}
                              className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                            >
                              <p className="break-words font-medium text-slate-800">{file.path}</p>
                              <p className="mt-1 text-xs text-slate-500">
                                {file.change_type} - {file.rationale}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                          Tests sugeridos
                        </p>
                        <div className="mt-2 space-y-2">
                          {patchPreview.suggested_tests.map((test) => (
                            <code
                              key={test}
                              className="block rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700"
                            >
                              {test}
                            </code>
                          ))}
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                          Diff preview
                        </p>
                        <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                          <code>{patchPreview.diff_preview}</code>
                        </pre>
                      </div>

                      <div>
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                            Cambios propuestos
                          </p>
                          {isProposingPatch ? (
                            <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                          ) : null}
                        </div>
                        {patchProposal ? (
                          <div className="mt-2 space-y-3">
                            {patchProposal.proposed_changes.map((change) => (
                              <div
                                key={`${change.path}-${change.change_type}`}
                                className="rounded-md border border-slate-200 bg-slate-50"
                              >
                                <div className="border-b border-slate-200 px-3 py-2">
                                  <p className="break-words text-sm font-medium text-slate-800">
                                    {change.path}
                                  </p>
                                  <p className="text-xs text-slate-500">{change.change_type}</p>
                                </div>
                                <pre className="max-h-64 overflow-auto p-3 text-xs leading-5 text-slate-700">
                                  <code>{change.content}</code>
                                </pre>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => void proposePatchChanges()}
                            disabled={isProposingPatch}
                            className="mt-2 inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 transition hover:border-sky-300 hover:bg-white hover:text-sky-900 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <Code2 className="h-4 w-4" />
                            Generar proposed_changes
                          </button>
                        )}
                      </div>

                      <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                        No aplica cambios. El gate de Sprint 24 exige cambios propuestos y
                        confirmacion explicita antes de escribir archivos.
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void checkPatchApplyGate()}
                          disabled={isCheckingPatchGate}
                          className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-medium text-white transition hover:bg-sky-900 disabled:cursor-not-allowed disabled:bg-slate-300"
                        >
                          {isCheckingPatchGate ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <ShieldCheck className="h-4 w-4" />
                          )}
                          Validar gate
                        </button>
                        <button
                          type="button"
                          onClick={() => void checkPatchApplyGate(true)}
                          disabled={isCheckingPatchGate || !patchProposal?.proposed_changes.length}
                          className="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 transition hover:border-red-300 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <AlertTriangle className="h-4 w-4" />
                          Aplicar con gate
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-3">
                      <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-500">
                        Cuando pidas crear o modificar codigo, el chat prepara un patch plan para
                        revisar antes de tocar archivos.
                      </p>
                      <button
                        type="button"
                        onClick={() => void sendMessage("Crea POST /api/v1/tools en FastAPI con tests.")}
                        disabled={isSending}
                        className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 transition hover:border-sky-300 hover:bg-white hover:text-sky-900 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Code2 className="h-4 w-4" />
                        Preparar patch plan
                      </button>
                    </div>
                  )}
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-950 p-4 text-sm leading-6 text-slate-200">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Sprint 24
                  </p>
                  <p className="mt-2 font-medium text-white">Apply Patch Gate v1</p>
                  {patchApplyPreview ? (
                    <div className="mt-3 space-y-3">
                      <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                          Estado
                        </p>
                        <p className="mt-1 font-semibold text-white">{patchApplyPreview.status}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          {patchApplyPreview.policy_action} - {patchApplyPreview.cyber_category}
                        </p>
                      </div>
                      {patchApplyPreview.validation_issues.length ? (
                        <div className="space-y-2">
                          {patchApplyPreview.validation_issues.map((issue) => (
                            <div
                              key={`${issue.code}-${issue.message}`}
                              className="rounded-md border border-amber-300/30 bg-amber-300/10 px-3 py-2 text-xs leading-5 text-amber-100"
                            >
                              <p className="font-medium">{issue.code}</p>
                              <p className="mt-1">{issue.message}</p>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      {patchApplyPreview.suggested_tests.length ? (
                        <code className="block rounded-md bg-black/30 px-3 py-2 text-xs text-slate-200">
                          {patchApplyPreview.suggested_tests[0]}
                        </code>
                      ) : null}
                      <p className="text-xs text-slate-400">
                        applied_files: {patchApplyPreview.applied_files.length}
                      </p>
                      {patchApplyPreview.snapshot_id ? (
                        <p className="break-all text-xs text-slate-400">
                          snapshot: {patchApplyPreview.snapshot_id}
                        </p>
                      ) : null}
                      {patchApplyPreview.status === "applied" ? (
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => void verifyAppliedPatch()}
                            disabled={isVerifyingPatch || !patchApplyPreview.suggested_tests.length}
                            className="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {isVerifyingPatch ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Terminal className="h-4 w-4" />
                            )}
                            Verificar tests
                          </button>
                          <button
                            type="button"
                            onClick={() => void rollbackAppliedPatch()}
                            disabled={isRollingBackPatch || !patchApplyPreview.snapshot_id}
                            className="inline-flex items-center gap-2 rounded-md border border-red-300/40 bg-red-400/10 px-3 py-2 text-sm font-medium text-red-100 transition hover:bg-red-400/20 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {isRollingBackPatch ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RotateCcw className="h-4 w-4" />
                            )}
                            Rollback
                          </button>
                        </div>
                      ) : null}
                      {patchVerifyPreview ? (
                        <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                            Verificacion
                          </p>
                          <p className="mt-1 font-semibold text-white">
                            {patchVerifyPreview.status}
                            {patchVerifyPreview.exit_code === null
                              ? ""
                              : ` - exit ${patchVerifyPreview.exit_code}`}
                          </p>
                          {(patchVerifyPreview.stdout || patchVerifyPreview.stderr) ? (
                            <pre className="mt-2 max-h-40 overflow-auto rounded bg-black/30 p-2 text-xs text-slate-200">
                              <code>{patchVerifyPreview.stdout || patchVerifyPreview.stderr}</code>
                            </pre>
                          ) : null}
                        </div>
                      ) : null}
                      {patchRollbackPreview ? (
                        <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                            Rollback
                          </p>
                          <p className="mt-1 font-semibold text-white">
                            {patchRollbackPreview.status}
                          </p>
                          <p className="mt-1 text-xs text-slate-400">
                            restaurados {patchRollbackPreview.restored_files.length} - eliminados{" "}
                            {patchRollbackPreview.deleted_files.length}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <p className="mt-1 text-slate-300">
                      Toma un patch_plan_id, exige confirmacion `APPLY_PATCH`, registra auditoria y
                      solo aplica cambios propuestos dentro del workspace.
                    </p>
                  )}
                </div>

                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Sprint 18
                      </p>
                      <h3 className="mt-1 text-base font-semibold text-slate-950">
                        Template preview
                      </h3>
                    </div>
                    <Code2 className="h-5 w-5 text-sky-700" />
                  </div>

                  {isRenderingTemplate ? (
                    <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generando plantilla...
                    </div>
                  ) : templatePreview ? (
                    <div className="mt-4 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          {templatePreview.artifact_name}
                        </span>
                        <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">
                          {templatePreview.language}
                        </span>
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                          review
                        </span>
                      </div>

                      {templatePreview.validation_issues.length ? (
                        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                          {templatePreview.validation_issues[0].message}
                        </div>
                      ) : null}

                      <pre className="max-h-80 overflow-auto rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                        <code>{templatePreview.content}</code>
                      </pre>

                      <button
                        type="button"
                        onClick={() => void navigator.clipboard.writeText(templatePreview.content)}
                        className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 transition hover:border-sky-300 hover:bg-white hover:text-sky-900"
                      >
                        <Copy className="h-4 w-4" />
                        Copiar preview
                      </button>

                      <p className="text-xs leading-5 text-slate-500">
                        Solo preview: DevCore no escribe archivos ni ejecuta esta plantilla.
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-500">
                      Cuando la interpretacion tenga suficientes parametros, aca aparece el codigo
                      generado para revisar.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-white/70 p-4 text-sm leading-6 text-slate-500">
                Cuando envies un mensaje, DevCore va a detectar intencion, parametros, riesgo y
                accion recomendada antes de responder.
              </div>
            )}

            <div className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Historial
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-slate-950">
                    Ultimas acciones
                  </h3>
                </div>
                <CheckCircle2 className="h-5 w-5 text-sky-700" />
              </div>
              {workbenchHistory.length ? (
                <div className="mt-4 space-y-2">
                  {workbenchHistory.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium text-slate-800">{item.title}</p>
                        <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500">
                          {item.kind}
                        </span>
                      </div>
                      <p className="mt-1 break-words text-xs leading-5 text-slate-500">
                        {item.detail}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-500">
                  Aca queda un rastro corto de interpretaciones, plantillas, sandbox y patch plans.
                </p>
              )}
            </div>

            <div className="mt-5 rounded-lg border border-slate-200 bg-slate-950 p-4 text-sm leading-6 text-slate-200">
              <p className="font-medium text-white">Regla de trabajo</p>
              <p className="mt-1 text-slate-300">
                Primero interpretar. Luego planificar. Los patch previews no aplican cambios; la
                ejecucion queda bajo sandbox, confirmacion y auditoria.
              </p>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
