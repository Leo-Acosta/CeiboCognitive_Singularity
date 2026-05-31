from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ceibo_core.models.schemas import DevCoreSafetyPolicy


@dataclass(frozen=True)
class DevCoreSafetyDecision:
    category: str
    policy_action: str
    risk_level: str
    requires_confirmation: bool
    double_confirmation_required: bool
    allowed_environment: str
    summary: str


DEFAULT_POLICY = DevCoreSafetyPolicy(
    policy_id="devcore_cyber_lab_policy",
    version="1.0",
    default_environment="local_dev",
    allow_categories=["general", "defensive_review", "safe_coding", "template_generation"],
    confirm_categories=["local_execution", "infrastructure_change", "credential_handling", "data_migration"],
    block_categories=[
        "credential_theft",
        "malware",
        "phishing",
        "evasion",
        "destructive_action",
        "unauthorized_access",
    ],
    double_confirm_risk_levels=["high", "blocked"],
)


class DevCoreSafetyLayer:
    def __init__(self) -> None:
        self._policy_path = Path(__file__).resolve().parents[3] / "config" / "devcore" / "lab_policy.yaml"
        self._policy = self._load_policy()

    def policy(self) -> DevCoreSafetyPolicy:
        return self._policy

    def classify(self, message: str, intent: str, base_risk_level: str) -> DevCoreSafetyDecision:
        normalized = message.lower()
        category = self._category_for_message(normalized, intent)
        risk_level = self._risk_for_category(category, base_risk_level)
        policy_action = self._policy_action_for_category(category)
        requires_confirmation = policy_action == "confirm" or risk_level in {"medium", "high", "blocked"}
        double_confirmation_required = (
            risk_level in set(self._policy.double_confirm_risk_levels)
            or category in {"credential_handling", "destructive_action", "unauthorized_access"}
        )
        if policy_action == "block":
            requires_confirmation = True
            double_confirmation_required = True
        return DevCoreSafetyDecision(
            category=category,
            policy_action=policy_action,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            double_confirmation_required=double_confirmation_required,
            allowed_environment=self._policy.default_environment,
            summary=self._summary(category, policy_action, risk_level),
        )

    def _load_policy(self) -> DevCoreSafetyPolicy:
        if not self._policy_path.exists():
            return DEFAULT_POLICY
        raw = self._policy_path.read_text(encoding="utf-8")
        values: dict[str, str | list[str]] = {}
        current_key: str | None = None
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- ") and current_key:
                values.setdefault(current_key, [])
                current = values[current_key]
                if isinstance(current, list):
                    current.append(stripped.removeprefix("- ").strip().strip('"'))
                continue
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                current_key = key.strip()
                value = value.strip().strip('"')
                values[current_key] = value if value else []
        return DevCoreSafetyPolicy(
            policy_id=str(values.get("policy_id") or DEFAULT_POLICY.policy_id),
            version=str(values.get("version") or DEFAULT_POLICY.version),
            default_environment=str(values.get("default_environment") or DEFAULT_POLICY.default_environment),
            allow_categories=self._list_value(values.get("allow_categories"), DEFAULT_POLICY.allow_categories),
            confirm_categories=self._list_value(values.get("confirm_categories"), DEFAULT_POLICY.confirm_categories),
            block_categories=self._list_value(values.get("block_categories"), DEFAULT_POLICY.block_categories),
            double_confirm_risk_levels=self._list_value(
                values.get("double_confirm_risk_levels"),
                DEFAULT_POLICY.double_confirm_risk_levels,
            ),
        )

    def _category_for_message(self, message: str, intent: str) -> str:
        if any(keyword in message for keyword in ("robar credenciales", "steal credentials", "dump passwords")):
            return "credential_theft"
        if any(keyword in message for keyword in ("malware", "ransomware", "backdoor", "botnet")):
            return "malware"
        if any(keyword in message for keyword in ("phishing", "suplantar login", "fake login")):
            return "phishing"
        if any(keyword in message for keyword in ("bypass", "evadir", "evasion", "desactivar antivirus")):
            return "evasion"
        if any(keyword in message for keyword in ("rm -rf", "format", "drop database", "reset --hard")):
            return "destructive_action"
        if any(keyword in message for keyword in ("sin permiso", "unauthorized", "explotar", "exploit public")):
            return "unauthorized_access"
        if any(keyword in message for keyword in ("credenciales", "secrets", "token", "api key", "password")):
            return "credential_handling"
        if intent == "execute_command":
            return "local_execution"
        if intent == "deploy_infra":
            return "infrastructure_change"
        if any(keyword in message for keyword in ("migracion", "alembic", "database", "db")):
            return "data_migration"
        if intent in {"create_endpoint", "modify_code"}:
            return "safe_coding"
        if any(keyword in message for keyword in ("auditoria", "hardening", "rbac", "logs")):
            return "defensive_review"
        return "general"

    def _policy_action_for_category(self, category: str) -> str:
        if category in set(self._policy.block_categories):
            return "block"
        if category in set(self._policy.confirm_categories):
            return "confirm"
        return "allow"

    def _risk_for_category(self, category: str, base_risk_level: str) -> str:
        if category in set(self._policy.block_categories):
            return "blocked"
        if category in {"credential_handling", "destructive_action", "unauthorized_access"}:
            return "high"
        if category in set(self._policy.confirm_categories):
            return "medium" if base_risk_level == "low" else base_risk_level
        return base_risk_level

    @staticmethod
    def _summary(category: str, policy_action: str, risk_level: str) -> str:
        if policy_action == "block":
            return f"Bloqueado por politica de laboratorio: {category}."
        if policy_action == "confirm":
            return f"Permitido solo con confirmacion explicita en entorno local: {category}."
        return f"Permitido en modo local controlado: {category}."

    @staticmethod
    def _list_value(value: str | list[str] | None, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return fallback


devcore_safety_layer = DevCoreSafetyLayer()
