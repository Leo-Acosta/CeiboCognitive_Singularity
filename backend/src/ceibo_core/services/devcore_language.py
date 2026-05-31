from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentRule:
    intent: str
    keywords: tuple[str, ...]
    required_parameters: tuple[str, ...] = ()


SYNONYMS: dict[str, str] = {
    "arregla": "fix",
    "corrige": "fix",
    "soluciona": "fix",
    "repara": "fix",
    "crea": "create",
    "agrega": "create",
    "anade": "create",
    "genera": "create",
    "implementa": "implement",
    "borra": "delete",
    "elimina": "delete",
    "quita": "delete",
    "muestra": "inspect",
    "revisa": "inspect",
    "analiza": "inspect",
    "explica": "explain",
    "ejecuta": "execute",
    "corre": "execute",
    "lanza": "execute",
    "despliega": "deploy",
}


INTENT_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        intent="external_information",
        keywords=("clima", "tiempo", "temperatura", "pronostico", "cotizacion", "precio actual"),
        required_parameters=("external_provider",),
    ),
    IntentRule(
        intent="create_endpoint",
        keywords=("endpoint", "ruta", "api route", "fastapi", "post ", "get "),
        required_parameters=("target_area", "http_method", "endpoint_path"),
    ),
    IntentRule(
        intent="modify_code",
        keywords=("fix", "create", "implement", "editar", "cambiar", "componente", "frontend", "backend"),
        required_parameters=("target_area",),
    ),
    IntentRule(
        intent="execute_command",
        keywords=("execute", "powershell", "bash", "comando", "script", "terminal"),
        required_parameters=("command_family",),
    ),
    IntentRule(
        intent="delete_or_cleanup",
        keywords=("delete", "remove", "limpiar", "reset", "prune"),
        required_parameters=("target_area",),
    ),
    IntentRule(
        intent="deploy_infra",
        keywords=("deploy", "docker", "compose", "kubernetes", "helm", "grafana"),
        required_parameters=("target_area",),
    ),
    IntentRule(
        intent="inspect_project",
        keywords=("inspect", "estado", "logs", "arquitectura", "archivo", "repo"),
    ),
    IntentRule(
        intent="explain_concept",
        keywords=("explain", "como funciona", "que es", "documenta"),
    ),
)


BLOCKED_KEYWORDS = (
    "malware",
    "ransomware",
    "phishing",
    "exfiltrar",
    "robar credenciales",
    "backdoor",
    "botnet",
)


HIGH_RISK_KEYWORDS = (
    "format",
    "rm -rf",
    "delete",
    "drop database",
    "reset --hard",
    "produccion",
    "production",
    "credenciales",
    "secrets",
    "token",
)


MEDIUM_RISK_KEYWORDS = (
    "execute",
    "powershell",
    "bash",
    "script",
    "docker compose down",
    "migracion",
    "alembic",
    "deploy",
)


TECHNOLOGIES = (
    "frontend",
    "backend",
    "fastapi",
    "react",
    "next",
    "docker",
    "postgres",
    "qdrant",
    "redis",
    "nats",
)


HTTP_METHODS = ("get", "post", "put", "patch", "delete")
