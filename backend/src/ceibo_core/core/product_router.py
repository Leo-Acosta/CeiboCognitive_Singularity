from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


ProductMode = Literal[
    "core",
    "legal",
    "empleo",
    "forense",
    "code",
    "economics",
    "finance",
    "agents",
    "reverse_engineering",
    "general",
]


@dataclass(frozen=True)
class HumanInteractionConfig:
    preserve_natural_dialogue: bool = True
    tone: str = "professional_argentine_spanish"
    ask_clarifying_questions: bool = True


@dataclass(frozen=True)
class ProductRoute:
    mode: ProductMode
    agent: str
    rag_namespace: str
    adapter: str
    guardrails: list[str]
    tools: list[str]
    human_interaction: HumanInteractionConfig

    def to_dict(self) -> dict:
        data = asdict(self)
        data["human_interaction"] = asdict(self.human_interaction)
        return data


MODE_ROUTES: dict[ProductMode, ProductRoute] = {
    "core": ProductRoute(
        mode="core",
        agent="ceibo_core_conversational_agent",
        rag_namespace="ceibo_core",
        adapter="ceibo_core_qwen7b_lora",
        guardrails=["human_interaction_preserved", "audit_required"],
        tools=["memory_search", "rag_search"],
        human_interaction=HumanInteractionConfig(),
    ),
    "legal": ProductRoute(
        mode="legal",
        agent="labor_law_agent",
        rag_namespace="ceibo_legal",
        adapter="ceibo_legal_qwen7b_lora",
        guardrails=["legal_review_required", "no_professional_replacement"],
        tools=["jurisprudence_search", "document_generator"],
        human_interaction=HumanInteractionConfig(),
    ),
    "empleo": ProductRoute(
        mode="empleo",
        agent="cv_agent",
        rag_namespace="ceibo_empleo",
        adapter="ceibo_empleo_qwen7b_lora",
        guardrails=["career_guidance_only", "no_fake_credentials"],
        tools=["cv_template_builder", "interview_feedback"],
        human_interaction=HumanInteractionConfig(),
    ),
    "forense": ProductRoute(
        mode="forense",
        agent="forensic_report_agent",
        rag_namespace="ceibo_forense",
        adapter="ceibo_forense_qwen7b_lora",
        guardrails=["authorized_defensive_only", "no_offensive_cyber"],
        tools=["chain_of_custody_builder", "incident_report_generator"],
        human_interaction=HumanInteractionConfig(),
    ),
    "code": ProductRoute(
        mode="code",
        agent="code_review_agent",
        rag_namespace="ceibo_code",
        adapter="ceibo_code_qwen_coder7b_lora",
        guardrails=["no_secret_exfiltration", "safe_execution_required"],
        tools=["repo_search", "test_runner"],
        human_interaction=HumanInteractionConfig(),
    ),
    "economics": ProductRoute(
        mode="economics",
        agent="economics_agent",
        rag_namespace="ceibo_economics",
        adapter="ceibo_economics_qwen7b_lora",
        guardrails=["no_personal_financial_advice", "scenario_based_outputs"],
        tools=["macro_report_generator", "risk_summary"],
        human_interaction=HumanInteractionConfig(),
    ),
    "finance": ProductRoute(
        mode="finance",
        agent="finance_agent",
        rag_namespace="ceibo_economics",
        adapter="ceibo_economics_qwen7b_lora",
        guardrails=["no_personal_financial_advice", "no_promised_returns"],
        tools=["valuation_calculator", "portfolio_risk"],
        human_interaction=HumanInteractionConfig(),
    ),
    "agents": ProductRoute(
        mode="agents",
        agent="planner_agent",
        rag_namespace="ceibo_agents",
        adapter="ceibo_agents_qwen7b_lora",
        guardrails=["human_approval_for_sensitive_actions", "audit_required"],
        tools=["mission_planner", "agent_run_report"],
        human_interaction=HumanInteractionConfig(),
    ),
    "reverse_engineering": ProductRoute(
        mode="reverse_engineering",
        agent="architecture_analysis_agent",
        rag_namespace="ceibo_reverse_engineering",
        adapter="ceibo_reverse_engineering_qwen7b_lora",
        guardrails=[
            "authorized_analysis_only",
            "no_ip_infringement",
            "no_drm_circumvention",
            "clean_room_required_for_reimplementation",
            "no_malware_reproduction",
        ],
        tools=[
            "architecture_mapper",
            "dependency_analyzer",
            "clean_room_spec_generator",
        ],
        human_interaction=HumanInteractionConfig(),
    ),
    "general": ProductRoute(
        mode="general",
        agent="general_assistant_agent",
        rag_namespace="ceibo_core",
        adapter="ceibo_core_qwen7b_lora",
        guardrails=["human_interaction_preserved", "safe_general_assistance"],
        tools=["memory_search"],
        human_interaction=HumanInteractionConfig(),
    ),
}


KEYWORDS: dict[ProductMode, tuple[str, ...]] = {
    "legal": ("ley", "legal", "contrato", "demanda", "laboral", "jurisprudencia"),
    "empleo": ("cv", "entrevista", "postulacion", "ats", "empleo", "trabajo"),
    "forense": ("forense", "evidencia", "custodia", "incidente", "logs", "ciber"),
    "code": ("python", "javascript", "java", "react", "fastapi", "codigo", "bug"),
    "economics": ("economia", "macro", "inflacion", "tipo de cambio", "riesgo pais"),
    "finance": ("finanzas", "trading", "valuacion", "dcf", "portfolio", "inversion"),
    "agents": ("agente", "autonomo", "planificar", "ejecutar", "herramienta"),
    "reverse_engineering": (
        "ingenieria inversa",
        "reverse engineering",
        "clean-room",
        "clean room",
        "interoperabilidad",
        "sistema legacy",
        "binario",
        "firmware",
        "protocolo",
        "arquitectura",
        "dependencias",
    ),
}


def classify_product_mode(user_message: str) -> ProductMode:
    normalized = user_message.casefold()
    for mode, keywords in KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return mode
    return "general"


def route_product_query(user_message: str, preferred_mode: ProductMode | None = None) -> dict:
    mode = preferred_mode or classify_product_mode(user_message)
    return MODE_ROUTES[mode].to_dict()
