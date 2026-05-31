from pathlib import Path
import re
import unicodedata

from ceibo_core.models.schemas import (
    AgentRole,
    DevCoreCapabilityPromotionDecision,
    DevCoreCapabilityPromotionRequest,
    DevCoreCapabilityRecord,
    DevCoreCapabilityStatus,
    DevCoreParseRequest,
    DevCoreParsedParameter,
    DevCoreParseResponse,
    DevCorePlanRequest,
    DevCorePlanResponse,
    DevCorePlanStep,
    DevCoreStatus,
    DevCoreValidationIssue,
    PromotionGateCheck,
)
from ceibo_core.services.devcore_language import (
    BLOCKED_KEYWORDS,
    HIGH_RISK_KEYWORDS,
    HTTP_METHODS,
    INTENT_RULES,
    MEDIUM_RISK_KEYWORDS,
    SYNONYMS,
    TECHNOLOGIES,
    IntentRule,
)
from ceibo_core.services.devcore_safety import DevCoreSafetyDecision, devcore_safety_layer


class DevCoreService:
    capabilities = [
        "repo-inspection",
        "change-planning",
        "test-routing",
        "template-engine",
        "cyber-safety-layer",
        "execution-sandbox",
        "patch-planner",
        "release-readiness",
        "safe-local-automation",
    ]

    def __init__(self) -> None:
        self._repo_root = Path(__file__).resolve().parents[4]
        self._capabilities: dict[str, DevCoreCapabilityRecord] = {
            "repo-inspection": DevCoreCapabilityRecord(
                capability_id="repo-inspection",
                name="Repo Inspection",
                description="Inspecciona estructura local del repositorio en modo solo lectura.",
                safety_score=95,
            ),
            "change-planning": DevCoreCapabilityRecord(
                capability_id="change-planning",
                name="Change Planning",
                description="Genera planes de cambio con pasos, targets y verificaciones.",
                safety_score=90,
            ),
            "test-routing": DevCoreCapabilityRecord(
                capability_id="test-routing",
                name="Test Routing",
                description="Recomienda checks segun el tipo de cambio solicitado.",
                safety_score=85,
            ),
            "template-engine": DevCoreCapabilityRecord(
                capability_id="template-engine",
                name="Template Engine",
                description="Genera plantillas seguras de codigo sin escribir ni ejecutar automaticamente.",
                safety_score=88,
            ),
            "cyber-safety-layer": DevCoreCapabilityRecord(
                capability_id="cyber-safety-layer",
                name="Cyber Safety Layer",
                description="Clasifica solicitudes cyber, aplica politica de laboratorio y bloquea usos peligrosos.",
                safety_score=92,
            ),
            "execution-sandbox": DevCoreCapabilityRecord(
                capability_id="execution-sandbox",
                name="Execution Sandbox",
                description="Ejecuta comandos allowlisted solo dentro del workspace con confirmacion y auditoria.",
                safety_score=80,
            ),
            "patch-planner": DevCoreCapabilityRecord(
                capability_id="patch-planner",
                name="Patch Planner",
                description="Prepara planes de patch y diff preview sin modificar archivos.",
                safety_score=90,
            ),
            "safe-local-automation": DevCoreCapabilityRecord(
                capability_id="safe-local-automation",
                name="Safe Local Automation",
                description="Prepara automatizacion local bajo gates de seguridad.",
                safety_score=70,
            ),
        }

    def status(self) -> DevCoreStatus:
        indexed_files = sum(1 for path in self._repo_root.rglob("*") if path.is_file() and ".git" not in path.parts)
        return DevCoreStatus(
            capabilities=self.capabilities,
            active_capabilities=sum(
                1 for capability in self._capabilities.values() if capability.status == DevCoreCapabilityStatus.ACTIVE
            ),
            repo_root=str(self._repo_root),
            indexed_files=indexed_files,
            writable=False,
        )

    def capabilities_overview(self) -> list[DevCoreCapabilityRecord]:
        return list(self._capabilities.values())

    def metrics(self) -> dict[str, int]:
        records = self.capabilities_overview()
        active = sum(1 for capability in records if capability.status == DevCoreCapabilityStatus.ACTIVE)
        approved = sum(1 for capability in records if capability.status == DevCoreCapabilityStatus.APPROVED)
        average_safety = round(sum(capability.safety_score for capability in records) / len(records))
        return {
            "total": len(records),
            "active": active,
            "approved": approved,
            "average_safety": average_safety,
        }

    def parse(self, request: DevCoreParseRequest) -> DevCoreParseResponse:
        normalized, normalized_terms = self._normalize_message(request.message)
        intent, confidence, sub_intents, matched_rule = self._intent_for_message(normalized)
        base_risk_level = self._risk_for_message(normalized)
        safety_decision = devcore_safety_layer.classify(
            message=normalized,
            intent=intent,
            base_risk_level=base_risk_level,
        )
        risk_level = safety_decision.risk_level
        parameters = self._parameters_for_message(normalized)
        missing_parameters = self._missing_parameters(matched_rule, parameters)
        validation_issues = self._validation_issues(
            normalized=normalized,
            intent=intent,
            risk_level=risk_level,
            parameters=parameters,
            missing_parameters=missing_parameters,
            safety_decision=safety_decision,
        )
        requires_confirmation = safety_decision.requires_confirmation
        recommended_action = self._recommended_action(
            intent=intent,
            risk_level=risk_level,
            policy_action=safety_decision.policy_action,
        )
        structured_response = self._structured_parse_response(
            intent=intent,
            confidence=confidence,
            risk_level=risk_level,
            parameters=parameters,
            missing_parameters=missing_parameters,
            validation_issues=validation_issues,
            recommended_action=recommended_action,
            safety_decision=safety_decision,
        )
        return DevCoreParseResponse(
            original_message=request.message,
            normalized_message=normalized,
            intent=intent,
            sub_intents=sub_intents,
            confidence=confidence,
            risk_level=risk_level,
            parameters=parameters,
            missing_parameters=missing_parameters,
            normalized_terms=normalized_terms,
            validation_issues=validation_issues,
            requires_confirmation=requires_confirmation,
            double_confirmation_required=safety_decision.double_confirmation_required,
            cyber_category=safety_decision.category,
            policy_action=safety_decision.policy_action,
            allowed_environment=safety_decision.allowed_environment,
            safety_summary=safety_decision.summary,
            recommended_action=recommended_action,
            structured_response=structured_response,
        )

    def promote_capability(
        self,
        request: DevCoreCapabilityPromotionRequest,
    ) -> DevCoreCapabilityPromotionDecision:
        capability = self._capabilities.get(request.capability_id)
        latest_eval = None
        if request.require_evaluation:
            from ceibo_core.services.evaluation_harness import evaluation_harness_service

            latest_eval = evaluation_harness_service.latest()
        checks = [
            PromotionGateCheck(
                name="capability_exists",
                passed=capability is not None,
                detail=request.capability_id,
            ),
            PromotionGateCheck(
                name="human_approval",
                passed=bool(request.approved_by),
                detail=request.approved_by or "sin aprobador",
            ),
            PromotionGateCheck(
                name="safety_score",
                passed=bool(capability and capability.safety_score >= request.min_safety_score),
                detail=f"{capability.safety_score if capability else 0}/100 >= {request.min_safety_score}",
            ),
            PromotionGateCheck(
                name="evaluation_available",
                passed=not request.require_evaluation or latest_eval is not None,
                detail=latest_eval.run_id if latest_eval else "sin evaluation run",
            ),
        ]
        if latest_eval is not None:
            devcore_score = latest_eval.category_scores.get("devcore", 0)
            checks.append(
                PromotionGateCheck(
                    name="devcore_evaluation_score",
                    passed=devcore_score >= 67,
                    detail=f"{devcore_score}/100 >= 67",
                )
            )
        approved = all(check.passed for check in checks)
        if capability is not None:
            status = DevCoreCapabilityStatus.ACTIVE if approved else DevCoreCapabilityStatus.BLOCKED
            capability = capability.model_copy(update={"status": status})
            self._capabilities[request.capability_id] = capability
        return DevCoreCapabilityPromotionDecision(
            capability_id=request.capability_id,
            approved=approved,
            capability=capability,
            checks=checks,
            evaluation_run_id=latest_eval.run_id if latest_eval else None,
        )

    def plan(self, request: DevCorePlanRequest) -> DevCorePlanResponse:
        normalized = request.goal.lower()
        targets = self._targets_for_goal(normalized)
        recommended_agent = self._agent_for_goal(normalized)
        steps = [
            DevCorePlanStep(
                order=1,
                action="inspect",
                target=", ".join(targets),
                safety="read-only repo scan before edits",
            ),
            DevCorePlanStep(
                order=2,
                action="design",
                target="minimal scoped change plan",
                safety="prefer existing project patterns",
            ),
            DevCorePlanStep(
                order=3,
                action="verify",
                target=self._verification_for_goal(normalized),
                safety="run checks before commit",
            ),
        ]
        return DevCorePlanResponse(
            goal=request.goal,
            summary=f"DevCore preparo una ruta local segura para: {request.goal}",
            recommended_agent=recommended_agent,
            steps=steps,
        )

    def _normalize_message(self, message: str) -> tuple[str, dict[str, str]]:
        normalized = " ".join(message.strip().lower().split())
        normalized = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
        used: dict[str, str] = {}
        for source, target in SYNONYMS.items():
            pattern = rf"\b{re.escape(source)}\b"
            if re.search(pattern, normalized):
                normalized = re.sub(pattern, target, normalized)
                used[source] = target
        return normalized, used

    def _intent_for_message(self, message: str) -> tuple[str, float, list[str], IntentRule | None]:
        matches: list[tuple[IntentRule, int]] = []
        for rule in INTENT_RULES:
            score = sum(1 for keyword in rule.keywords if keyword in message)
            if score:
                matches.append((rule, score))

        if not matches:
            return "general_request", 0.48, [], None

        matched_rule, score = max(matches, key=lambda item: item[1])
        sub_intents = [rule.intent for rule, rule_score in matches if rule.intent != matched_rule.intent and rule_score > 0]
        confidence = min(0.96, 0.66 + score * 0.12 + min(len(sub_intents), 2) * 0.04)
        return matched_rule.intent, confidence, sub_intents, matched_rule

    def _risk_for_message(self, message: str) -> str:
        if any(keyword in message for keyword in BLOCKED_KEYWORDS):
            return "blocked"
        if any(keyword in message for keyword in HIGH_RISK_KEYWORDS):
            return "high"
        if any(keyword in message for keyword in MEDIUM_RISK_KEYWORDS):
            return "medium"
        return "low"

    def _parameters_for_message(self, message: str) -> list[DevCoreParsedParameter]:
        parameters: list[DevCoreParsedParameter] = []
        targets = self._targets_for_goal(message)
        if targets != ["repo root"]:
            parameters.append(
                DevCoreParsedParameter(
                    name="target_area",
                    value=", ".join(targets),
                    confidence=0.78,
                )
            )
        technologies = [tech for tech in TECHNOLOGIES if tech in message]
        if technologies:
            parameters.append(
                DevCoreParsedParameter(
                    name="technology",
                    value=", ".join(technologies),
                    confidence=0.86,
                    source="keyword",
                )
            )
        endpoint_path = self._endpoint_path_for_message(message)
        if endpoint_path:
            parameters.append(
                DevCoreParsedParameter(
                    name="endpoint_path",
                    value=endpoint_path,
                    confidence=0.9,
                    source="pattern",
                )
            )
        http_method = self._http_method_for_message(message)
        if http_method:
            parameters.append(
                DevCoreParsedParameter(
                    name="http_method",
                    value=http_method,
                    confidence=0.82,
                    source="keyword",
                )
            )
        command_family = self._command_family_for_message(message)
        if command_family:
            parameters.append(
                DevCoreParsedParameter(
                    name="command_family",
                    value=command_family,
                    confidence=0.78,
                    source="keyword",
                )
            )
        if "test" in message or "prueba" in message:
            parameters.append(
                DevCoreParsedParameter(
                    name="verification",
                    value=self._verification_for_goal(message),
                    confidence=0.72,
                )
            )
        if any(keyword in message for keyword in ("clima", "tiempo", "temperatura", "pronostico")):
            parameters.append(
                DevCoreParsedParameter(
                    name="external_provider",
                    value="weather api required",
                    confidence=0.7,
                    source="keyword",
                )
            )
        return parameters

    def _missing_parameters(
        self,
        rule: IntentRule | None,
        parameters: list[DevCoreParsedParameter],
    ) -> list[str]:
        if rule is None:
            return []
        found = {parameter.name for parameter in parameters}
        return [name for name in rule.required_parameters if name not in found]

    def _endpoint_path_for_message(self, message: str) -> str | None:
        match = re.search(r"(?<!:)\/(?:api\/)?[a-z0-9_\-\/{}]+", message)
        return match.group(0) if match else None

    def _http_method_for_message(self, message: str) -> str | None:
        for method in HTTP_METHODS:
            if re.search(rf"\b{method}\b", message):
                return method.upper()
        if "endpoint" in message and any(keyword in message for keyword in ("create", "agregar", "agrega")):
            return "POST"
        return None

    def _command_family_for_message(self, message: str) -> str | None:
        for family in ("powershell", "bash", "docker", "pytest", "npm"):
            if family in message:
                return family
        if "script" in message or "comando" in message or "execute" in message:
            return "shell"
        return None

    def _validation_issues(
        self,
        normalized: str,
        intent: str,
        risk_level: str,
        parameters: list[DevCoreParsedParameter],
        missing_parameters: list[str],
        safety_decision: DevCoreSafetyDecision,
    ) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        if safety_decision.policy_action == "block":
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="blocked_by_lab_policy",
                    message=safety_decision.summary,
                )
            )
        if safety_decision.double_confirmation_required and safety_decision.policy_action != "block":
            issues.append(
                DevCoreValidationIssue(
                    severity="warning",
                    code="double_confirmation_required",
                    message="Requiere doble confirmacion explicita antes de cualquier accion.",
                )
            )
        if risk_level == "blocked":
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="blocked_cyber_or_harmful_request",
                    message="La solicitud contiene señales que deben bloquearse antes de generar acciones.",
                )
            )
        if risk_level == "high":
            issues.append(
                DevCoreValidationIssue(
                    severity="warning",
                    code="high_risk_confirmation_required",
                    message="Requiere confirmacion explicita y alcance acotado antes de continuar.",
                )
            )
        if missing_parameters:
            issues.append(
                DevCoreValidationIssue(
                    severity="info",
                    code="missing_required_parameters",
                    message=f"Faltan parametros para completar la interpretacion: {', '.join(missing_parameters)}.",
                )
            )
        if intent in {"modify_code", "create_endpoint", "execute_command", "delete_or_cleanup"} and not parameters:
            issues.append(
                DevCoreValidationIssue(
                    severity="info",
                    code="missing_target_area",
                    message="Conviene especificar modulo, archivo o tecnologia objetivo.",
                )
            )
        if intent == "external_information":
            issues.append(
                DevCoreValidationIssue(
                    severity="info",
                    code="external_provider_required",
                    message="Esta solicitud requiere una fuente externa o integracion especifica.",
                )
            )
        if "todo" in normalized or "todo el proyecto" in normalized:
            issues.append(
                DevCoreValidationIssue(
                    severity="warning",
                    code="scope_too_broad",
                    message="El alcance parece amplio; se recomienda dividirlo en pasos pequenos.",
                )
            )
        return issues

    def _recommended_action(self, intent: str, risk_level: str, policy_action: str = "allow") -> str:
        if policy_action == "block" or risk_level == "blocked":
            return "bloquear y pedir reformulacion segura"
        if risk_level == "high":
            return "pedir confirmacion y generar solo plan"
        if policy_action == "confirm":
            return "pedir confirmacion antes de preparar acciones"
        if intent == "inspect_project":
            return "inspeccionar en modo solo lectura"
        if intent == "create_endpoint":
            return "pedir ruta/metodo si faltan y generar plan FastAPI con tests"
        if intent == "modify_code":
            return "generar plan de cambio antes de editar"
        if intent == "execute_command":
            return "preparar comando sin ejecutar automaticamente"
        if intent == "external_information":
            return "pedir o conectar fuente externa antes de afirmar datos"
        if intent in {"delete_or_cleanup", "deploy_infra"}:
            return "generar plan y pedir confirmacion antes de tocar estado"
        return "responder y proponer siguiente paso"

    def _structured_parse_response(
        self,
        intent: str,
        confidence: float,
        risk_level: str,
        parameters: list[DevCoreParsedParameter],
        missing_parameters: list[str],
        validation_issues: list[DevCoreValidationIssue],
        recommended_action: str,
        safety_decision: DevCoreSafetyDecision,
    ) -> str:
        parameter_text = ", ".join(f"{item.name}={item.value}" for item in parameters) or "sin parametros claros"
        missing_text = ", ".join(missing_parameters) or "ninguno"
        issue_text = "; ".join(issue.message for issue in validation_issues) or "sin bloqueos de validacion"
        return (
            f"Interprete la solicitud como `{intent}` con confianza {confidence:.0%}. "
            f"Riesgo: {risk_level}. Categoria cyber: {safety_decision.category}. "
            f"Politica: {safety_decision.policy_action}. Parametros: {parameter_text}. "
            f"Faltantes: {missing_text}. "
            f"Validacion: {issue_text}. Accion recomendada: {recommended_action}."
        )

    def _targets_for_goal(self, goal: str) -> list[str]:
        targets: list[str] = []
        if any(keyword in goal for keyword in ("frontend", "dashboard", "ui")):
            targets.append("frontend/app")
        if any(keyword in goal for keyword in ("api", "backend", "endpoint", "fastapi")):
            targets.append("backend/src/ceibo_core/api")
        if any(keyword in goal for keyword in ("db", "database", "alembic", "persistencia")):
            targets.append("backend/migrations")
        if any(keyword in goal for keyword in ("test", "eval", "quality")):
            targets.append("backend/tests")
        return targets or ["repo root"]

    def _agent_for_goal(self, goal: str) -> AgentRole:
        if any(keyword in goal for keyword in ("security", "seguridad", "rbac", "audit")):
            return AgentRole.CYBERSECURITY
        if any(keyword in goal for keyword in ("docker", "compose", "deploy", "ci", "alembic")):
            return AgentRole.INFRASTRUCTURE
        if any(keyword in goal for keyword in ("memoria", "knowledge", "rag")):
            return AgentRole.MEMORY
        return AgentRole.AUTOMATION

    def _verification_for_goal(self, goal: str) -> str:
        if any(keyword in goal for keyword in ("frontend", "dashboard", "ui")):
            return "npm run build"
        if any(keyword in goal for keyword in ("docker", "compose")):
            return "docker compose config"
        return "python -m pytest backend/tests"


devcore_service = DevCoreService()
