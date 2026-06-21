from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


VISION_ES = (
    "Ceibo AI es una plataforma argentina de inteligencia artificial aplicada "
    "que combina modelos abiertos, datos locales, interaccion humana natural, "
    "agentes especializados, RAG documental, fine-tuning y herramientas "
    "profesionales para asistir trabajo real en empleo, derecho, "
    "ciberseguridad, economia, programacion y automatizacion."
)

SLOGAN = "Ceibo AI: la inteligencia argentina que trabaja con vos."

CORE_DEF = (
    "Ceibo Core es el cerebro conversacional, cognitivo y agente de Ceibo AI, "
    "capaz de dialogar con humanos de forma natural y ademas operar verticales "
    "especializadas."
)

DATASET_SCHEMA = {
    "instruction": "",
    "input": "",
    "response": "",
    "tags": [],
    "source": "",
    "rating": 0,
    "metadata": {
        "vertical": "",
        "risk_level": "",
        "language": "es-AR",
        "version": "v0.1",
    },
}


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip() + "\n", encoding="utf-8")


def write_json(path: str, data: object) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: str, rows: list[dict]) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def md(title: str, body: str) -> str:
    return f"# {title}\n\n{SLOGAN}\n\n{CORE_DEF}\n\n{body.strip()}\n"


def product_body(name: str, focus: str, extra: str = "") -> str:
    return f"""
## Rol

{name} forma parte de Ceibo AI como vertical o componente comercial. Su
responsabilidad es convertir conversacion humana, datos locales, RAG,
herramientas y agentes en asistencia profesional medible.

## Enfoque

{focus}

## Principios

- Ceibo Core conserva el dialogo natural con el usuario.
- Las respuestas deben ser utiles, trazables y auditables.
- Las acciones sensibles requieren aprobacion humana.
- No se usan datos personales reales ni informacion confidencial en ejemplos.
- Los adaptadores LoRA/QLoRA se versionan y se comparan contra baseline.

{extra}
"""


def create_products() -> None:
    write(
        "products/README.md",
        md(
            "Products",
            f"""
Ceibo AI organiza el repositorio en dos niveles: la plataforma comercial
Ceibo AI y el cerebro interno Ceibo Core.

## Plataforma

{VISION_ES}

## Niveles

- Ceibo AI: marca comercial, SaaS local-first y cloud-ready, experiencia de
  usuario profesional, verticales y producto vendible.
- Ceibo Core: cerebro conversacional, cognitivo y agente, memoria, RAG,
  router de modelos, router de herramientas, entrenamiento, evaluacion,
  seguridad y auditoria.

## Verticales

- ceibo-empleo
- ceibo-legal
- ceibo-forense
- ceibo-code
- ceibo-economics
- ceibo-agents
""",
        ),
    )

    ceibo_ai_files = {
        "README.md": product_body(
            "Ceibo AI",
            "Plataforma argentina de IA aplicada al trabajo profesional real.",
            "No se vende como ChatGPT argentino ni como modelo fundacional propio.",
        ),
        "product_vision.md": product_body(
            "Vision de producto",
            "SaaS local-first con conversacion humana natural, documentos, agentes y RAG por vertical.",
        ),
        "commercial_positioning.md": product_body(
            "Posicionamiento comercial",
            "La ventaja competitiva combina especializacion argentina, datasets propios, RAG, LoRA, seguridad y Ceibo Core como cerebro conversacional.",
        ),
        "pricing_strategy.md": product_body(
            "Pricing",
            "Planes orientativos: gratuito, profesional, premium e institucional, con limites por uso, vertical y despliegue.",
        ),
        "launch_plan.md": product_body(
            "Plan de lanzamiento",
            "MVP, beta privada, pilotos profesionales, demos verticales y comunidad tecnica local.",
        ),
        "roadmap.md": product_body(
            "Roadmap",
            "Activar datasets reales, Qwen 3B smoke test, Qwen 7B QLoRA, RAG legal/economico y MVP comercial.",
        ),
    }
    for filename, content in ceibo_ai_files.items():
        write(f"products/ceibo-ai/{filename}", md(filename.removesuffix(".md").replace("_", " ").title(), content))

    core_files = {
        "README.md": product_body(
            "Ceibo Core",
            "Cerebro interno conversacional, cognitivo y agente de Ceibo AI.",
        ),
        "core_architecture.md": "Ceibo Core integra conversacion, memoria, RAG, agentes, modelos, herramientas, evaluacion, seguridad y auditoria en una arquitectura entrenable.",
        "human_interaction_layer.md": """
## Proposito

La Human Interaction Layer preserva la capacidad de Ceibo Core para conversar
con personas en lenguaje natural. Incluye dialogo sostenido, tono humano
profesional, empatia, adaptacion al usuario, memoria contextual cuando este
habilitada, continuidad conversacional y futura interaccion por texto/audio.

## Voz futura

La capa queda preparada para speech-to-text, text-to-speech, turn-taking,
interrupciones y loops conversacionales seguros. La voz no reemplaza la
trazabilidad ni los controles humanos.

## Limites

Ceibo Core puede sonar natural, pero no debe fingir ser una persona humana
real. Debe explicar capacidades, limites y necesidad de revision humana cuando
corresponda.
""",
        "conversational_brain.md": """
Ceibo Core no es solo un router. Es cerebro conversacional, cerebro cognitivo,
orquestador de agentes, coordinador de verticales, supervisor de herramientas,
memoria activa, interfaz humana, sistema de seguridad y motor de razonamiento
operativo.

El usuario conversa con Ceibo Core. Internamente, Core puede activar prompts,
RAG, adaptadores, herramientas y agentes, pero la respuesta final mantiene
claridad, naturalidad, contexto y utilidad.
""",
        "cognitive_architecture.md": "La arquitectura cognitiva separa percepcion conversacional, memoria, planificacion, uso de herramientas, evaluacion y respuesta final.",
        "agent_orchestration.md": "Ceibo Core orquesta agentes investigadores, redactores, criticos, ejecutores, memoria, herramientas y safety supervisor con human-in-the-loop.",
        "memory_and_rag.md": "La memoria conversa con RAG vertical. La memoria guarda contexto permitido; RAG aporta fuentes trazables por namespace.",
        "model_router.md": "El router de modelos selecciona Qwen, Mistral, Ollama local, vLLM o cloud segun configuracion, riesgo y costo.",
        "tool_router.md": "El router de herramientas expone busquedas, generadores, calculadoras y acciones permitidas con auditoria.",
        "vertical_operator.md": """
Ceibo Core opera modos core, legal, empleo, forense, code, economics, finance,
agents y general. Puede recibir una conversacion humana comun y decidir, sin
perder naturalidad, que vertical, agente, RAG, herramienta, prompt o adaptador
usar.

La seleccion interna nunca reemplaza la conversacion humana: la clasificacion
de modo es una funcion privada de Core y la respuesta se mantiene clara,
argentina, profesional y util.
""",
        "safety_and_audit.md": "Toda accion sensible requiere guardrails, trazabilidad, auditoria y aprobacion humana cuando corresponda.",
    }
    for filename, content in core_files.items():
        write(f"products/ceibo-core/{filename}", md(filename.removesuffix(".md").replace("_", " ").title(), content))

    verticals = {
        "ceibo-empleo": {
            "focus": "CV argentino, entrevistas, ATS, postulaciones, cartas, empleabilidad y entrenamiento por rol.",
            "agents": ["cv_agent", "interview_agent", "ats_agent", "job_application_agent"],
            "prompts": ["empleo_system_prompt", "cv_prompt", "interview_prompt", "ats_prompt"],
            "templates": ["cv_template", "interview_feedback", "cover_letter"],
        },
        "ceibo-legal": {
            "focus": "Derecho argentino, borradores, escritos, contratos, laboral, civil, penal, administrativo, FFSS, FFAA, penitenciario y jurisprudencia.",
            "guardrail": "legal_guardrails.md",
            "agents": ["labor_law_agent", "civil_law_agent", "criminal_law_agent", "administrative_law_agent", "penitentiary_law_agent", "ffss_ffaa_agent", "jurisprudence_agent"],
            "prompts": ["legal_system_prompt", "labor_law_prompt", "civil_law_prompt", "criminal_law_prompt", "administrative_law_prompt", "jurisprudence_prompt"],
            "templates": ["demanda_laboral", "contestacion_demanda", "contrato", "carta_documento", "recurso_administrativo", "informe_juridico"],
        },
        "ceibo-forense": {
            "focus": "Ciberseguridad defensiva, laboratorio autorizado, evidencia digital, cadena de custodia, blockchain, deepfake, IoT e informes.",
            "guardrail": "cyber_guardrails.md",
            "agents": ["forensic_report_agent", "evidence_chain_agent", "osint_agent", "blockchain_agent", "deepfake_agent", "iot_forensics_agent", "defensive_cyber_agent"],
            "prompts": ["forensic_system_prompt", "evidence_prompt", "blockchain_prompt", "deepfake_prompt", "iot_prompt"],
            "templates": ["forensic_report", "chain_of_custody", "incident_report", "blockchain_tracing_report", "deepfake_analysis_report"],
        },
        "ceibo-code": {
            "focus": "Python, JavaScript, Java, TypeScript, CSS, React, FastAPI, backend, frontend, DevOps, debugging, testing y documentacion.",
            "agents": ["python_agent", "javascript_agent", "java_agent", "frontend_agent", "backend_agent", "devops_agent", "code_review_agent"],
            "prompts": ["code_system_prompt", "python_prompt", "javascript_prompt", "java_prompt", "fastapi_prompt", "react_prompt"],
            "templates": ["api_spec", "bug_report", "code_review", "software_architecture"],
        },
        "ceibo-economics": {
            "focus": "Finanzas, trading educativo, valuacion, DCF, multiplos, riesgo, reportes macro, economia argentina y negocios.",
            "guardrail": "finance_guardrails.md",
            "agents": ["finance_agent", "trading_education_agent", "valuation_agent", "portfolio_risk_agent", "economics_agent", "country_report_agent", "business_economics_agent"],
            "prompts": ["finance_system_prompt", "economics_system_prompt", "valuation_prompt", "trading_education_prompt", "macro_report_prompt", "business_economics_prompt"],
            "templates": ["macro_country_report", "company_valuation_report", "trading_plan_template", "portfolio_risk_report", "economic_business_report"],
            "tools": ["valuation_calculator.py", "dcf_model.py", "multiples_analysis.py", "portfolio_risk.py", "macro_report_generator.py", "trading_education_simulator.py"],
        },
        "ceibo-agents": {
            "focus": "Agentes autonomos con planificacion, ejecucion supervisada, memoria, herramientas, safety supervisor, auditoria y limites.",
            "guardrail": "autonomous_agent_policy.md",
            "agents": ["planner_agent", "researcher_agent", "executor_agent", "critic_agent", "memory_agent", "safety_supervisor_agent"],
            "prompts": ["agents_system_prompt", "planner_prompt", "executor_prompt", "safety_prompt"],
            "templates": ["mission_plan", "agent_run_report", "audit_log"],
        },
    }
    for slug, spec in verticals.items():
        write(f"products/{slug}/README.md", md(slug, product_body(slug, spec["focus"])))
        write(f"products/{slug}/product_spec.md", md("Product Spec", product_body(slug, spec["focus"])))
        if "guardrail" in spec:
            write(f"products/{slug}/{spec['guardrail']}", guardrail_doc(slug))
        for agent in spec["agents"]:
            write(f"products/{slug}/agents/{agent}.md", agent_doc(slug, agent))
        for prompt in spec["prompts"]:
            write(f"products/{slug}/prompts/{prompt}.md", prompt_doc(slug, prompt))
        for template in spec["templates"]:
            write(f"products/{slug}/templates/{template}.md", template_doc(slug, template))
        for tool in spec.get("tools", []):
            write(f"products/{slug}/tools/{tool}", tool_stub(tool))


def guardrail_doc(slug: str) -> str:
    details = {
        "ceibo-legal": "Asistencia legal, no reemplazo de abogado, revision humana, no inventar jurisprudencia, no prometer resultado.",
        "ceibo-forense": "Solo defensa, laboratorio autorizado, CTF, compliance y forense. No intrusiones, malware, evasion, persistencia ni robo de credenciales.",
        "ceibo-economics": "Educacion financiera, escenarios y riesgos. No asesoramiento personalizado, promesas de rentabilidad ni senales directas de compra/venta.",
        "ceibo-agents": "Autonomia limitada, aprobacion humana para acciones sensibles, auditoria y reversibilidad cuando aplique.",
    }.get(slug, "Guardrails especificos por vertical.")
    return md("Guardrails", f"## Reglas\n\n{details}\n\n## Human-in-the-loop\n\nLas decisiones sensibles requieren aprobacion humana explicita y registro de auditoria.")


def agent_doc(slug: str, agent: str) -> str:
    return md(agent, f"## Mision\n\nAgente especializado de {slug}. Opera bajo Ceibo Core, preserva dialogo natural y respeta guardrails.\n\n## Salida esperada\n\nPlan breve, evidencia usada, respuesta profesional y trazabilidad.")


def prompt_doc(slug: str, prompt: str) -> str:
    return md(prompt, f"## Prompt base\n\nActua como modulo {slug} coordinado por Ceibo Core. Responde en espanol argentino claro, pide aclaraciones si faltan datos y no ocultes limites.")


def template_doc(slug: str, template: str) -> str:
    return md(template, f"## Template\n\n- Objetivo\n- Contexto\n- Analisis\n- Supuestos\n- Riesgos\n- Proximos pasos\n\nUsar solo datos provistos o fuentes trazables.")


def tool_stub(tool: str) -> str:
    return f'"""Conceptual placeholder for {tool}.\n\nReal financial calculations must declare assumptions and risks.\n"""\n\n\ndef run(*args, **kwargs):\n    raise NotImplementedError("Tool skeleton only; implement with validated formulas before production use.")\n'


def create_docs() -> None:
    docs = {
        "docs/ceibo-ai-rag-architecture.md": """
# Ceibo AI RAG Architecture

RAG usa documentos curados por vertical: leyes, jurisprudencia validada,
plantillas, manuales, KB tecnica, reportes anonimizados y guias internas. Los
documentos se chunkearan por estructura semantica, version, fuente y riesgo.

Qdrant o pgvector almacenan embeddings separados por namespace: ceibo_core,
ceibo_legal, ceibo_empleo, ceibo_forense, ceibo_code, ceibo_economics y
ceibo_agents. Ceibo Core consulta RAG sin perder dialogo natural: primero
entiende la conversacion, luego recupera evidencia, cita fuentes y responde
con claridad.

Si no hay base documental suficiente, Ceibo Core debe decirlo, pedir fuentes o
responder como orientacion general. Cada respuesta RAG debe registrar consulta,
namespace, chunks, version, fuentes y decision de guardrails.
""",
        "docs/ceibo-ai-product-router.md": """
# Ceibo AI Product Router

El router clasifica consultas en mode: core, legal, empleo, forense, code,
economics, finance, agents o general. Cada modo puede activar system prompt,
adaptador LoRA, RAG, herramientas, guardrails, evaluacion y template de salida.

El router no reemplaza la conversacion humana. Es una funcion interna de
Ceibo Core: el usuario sigue hablando con Ceibo Core, que mantiene tono natural,
preguntas aclaratorias, memoria y respuesta profesional.
""",
        "docs/ceibo-ai-agent-architecture.md": """
# Ceibo AI Agent Architecture

Ceibo Core orquesta agentes investigadores, redactores, criticos, supervisores,
memoria, herramientas, evaluacion y safety supervisor. El flujo recomendado es:
entender conversacion, clasificar modo, recuperar contexto, planificar,
ejecutar solo acciones permitidas, criticar, aplicar guardrails y responder.

Las acciones sensibles requieren human-in-the-loop: confirmacion explicita,
registro de auditoria y posibilidad de cancelar.
""",
        "docs/ceibo-ai-training-lifecycle.md": """
# Ceibo AI Training Lifecycle

1. Recoleccion de ejemplos.
2. Limpieza.
3. Anonimizacion.
4. Curacion.
5. Validacion.
6. Fine-tuning QLoRA.
7. Evaluacion.
8. Comparacion con baseline.
9. Registro de version.
10. Publicacion de adaptador.
11. Monitoreo.
12. Reentrenamiento.
13. Evaluacion de la capacidad conversacional humana de Ceibo Core.
14. Evaluacion de capacidad para operar verticales sin perder dialogo natural.

Qwen 3B sirve para smoke tests; Qwen 7B como base general inicial; Qwen Coder
7B para Ceibo Code; Mistral queda como alternativa. Ollama sirve para
ejecucion local/demo. QLoRA requiere modelos compatibles con
HuggingFace/Transformers y no directamente GGUF/Ollama.
""",
        "docs/ceibo-ai-safety-policy.md": """
# Ceibo AI Safety Policy

La politica cubre seguridad legal, financiera, ciber, agentes autonomos,
privacidad, datos personales, secretos, evidencia digital, human-in-the-loop,
limites del sistema, seguridad conversacional y limites de humanizacion.

Ceibo Core puede dialogar naturalmente, pero no debe enganar al usuario
haciendose pasar por una persona humana real. Debe exponer limites, pedir
revision profesional cuando corresponda y bloquear usos ilegales o daninos.
""",
        "docs/ceibo-core-human-conversation-and-voice.md": """
# Ceibo Core Human Conversation And Voice

Ceibo Core conserva conversacion natural por texto, memoria conversacional,
tono profesional, turn-taking, manejo de interrupciones, clarificacion,
empatia, limites, seguridad y adaptacion al usuario.

La arquitectura futura de voz contempla speech-to-text, text-to-speech y un
conversation loop auditado. La voz debe preservar consentimiento, privacidad,
no engano y control humano para acciones sensibles.
""",
        "docs/ceibo-ai-commercial-roadmap.md": """
# Ceibo AI Commercial Roadmap

MVP con Ceibo Core conversacional, RAG inicial, verticales empleo/legal/code y
demo local con Ollama. Luego beta privada, plan gratuito, profesional, premium
e institucional. La estrategia combina comunidad, autoridad tecnica, landing
page, demos reales, primeros usuarios y contenido educativo.

Ceibo Core es el diferencial: cerebro conversacional, cognitivo y agente que
opera verticales sin perder dialogo humano natural.
""",
        "docs/ceibo-ai-investor-brief.md": """
# Ceibo AI Investor Brief

Problema: profesionales argentinos necesitan IA especializada, trazable y
adaptada a datos locales. Solucion: Ceibo AI, plataforma de IA aplicada con
Ceibo Core como cerebro conversacional, cognitivo y agente.

Tecnologia: modelos abiertos, Qwen/Mistral, RAG, LoRA/QLoRA, agentes,
herramientas, memoria, safety y auditoria. Moat: especializacion argentina,
datasets propios, flujos reales, verticales integradas y Human Interaction
Layer preservada.

Riesgos: calidad de datos, regulacion, seguridad, costo de inferencia y
adopcion. Mitigaciones: curacion, evaluaciones, guardrails, local-first,
cloud-ready y human-in-the-loop.
""",
    }
    for path, content in docs.items():
        write(path, content)


def create_rag() -> None:
    write("rag/README.md", "# RAG\n\nNamespaces documentales por vertical. Usar placeholders hasta cargar fuentes curadas y anonimizadas.\n")
    expected = {
        "ceibo_core": "Identidad, arquitectura, memoria, conversaciones, politicas y evaluaciones.",
        "ceibo_legal": "Normativa argentina, jurisprudencia validada, modelos y doctrina permitida.",
        "ceibo_empleo": "CV, entrevistas, ATS, perfiles laborales y guias de empleabilidad.",
        "ceibo_forense": "Guias defensivas, cadena de custodia, reportes, logs anonimizados y laboratorios.",
        "ceibo_code": "Documentacion tecnica, patrones, APIs, runbooks y guias de testing.",
        "ceibo_economics": "Series publicas, reportes macro, metodos de valuacion y supuestos.",
        "ceibo_agents": "Politicas de autonomia, playbooks, herramientas y auditoria.",
    }
    for namespace, description in expected.items():
        write(f"rag/{namespace}/README.md", f"# {namespace}\n\nDocumentos esperados: {description}\n\nNo cargar secretos, datos personales reales ni documentos no autorizados.\n")


def config(base_model: str, dataset: str, output: str, notes: str) -> dict:
    return {
        "base_model": base_model,
        "dataset_path": dataset,
        "output_dir": output,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "batch_size": 1,
        "gradient_accumulation_steps": 8,
        "learning_rate": 2e-4,
        "max_seq_length": 2048,
        "num_train_epochs": 1,
        "save_steps": 50,
        "logging_steps": 5,
        "bf16": False,
        "fp16": True,
        "load_in_4bit": True,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "notes": notes,
    }


def create_training() -> None:
    configs = {
        "ceibo_core_qwen3b_smoke.json": config("Qwen/Qwen2.5-3B-Instruct", "training/datasets/ceibo_core/seed.jsonl", "models/adapters/ceibo-core-qwen3b-smoke-v0.1", "Smoke test conversacional de Ceibo Core."),
        "ceibo_core_qwen7b_lora.json": config("Qwen/Qwen2.5-7B-Instruct", "training/datasets/ceibo_core/curated.jsonl", "models/adapters/ceibo-core-qwen7b-lora-v0.1", "Base general inicial para Ceibo Core."),
        "ceibo_legal_qwen7b_lora.json": config("Qwen/Qwen2.5-7B-Instruct", "training/datasets/ceibo_legal/curated.jsonl", "models/adapters/ceibo-legal-qwen7b-lora-v0.1", "Asistencia legal argentina con revision humana."),
        "ceibo_empleo_qwen7b_lora.json": config("Qwen/Qwen2.5-7B-Instruct", "training/datasets/ceibo_empleo/curated.jsonl", "models/adapters/ceibo-empleo-qwen7b-lora-v0.1", "CV, entrevistas y empleabilidad."),
        "ceibo_forense_qwen7b_lora.json": config("Qwen/Qwen2.5-7B-Instruct", "training/datasets/ceibo_forense/curated.jsonl", "models/adapters/ceibo-forense-qwen7b-lora-v0.1", "Forense y ciberseguridad defensiva autorizada."),
        "ceibo_code_qwen_coder7b_lora.json": config("Qwen/Qwen2.5-Coder-7B-Instruct", "training/datasets/ceibo_code/curated.jsonl", "models/adapters/ceibo-code-qwen-coder7b-lora-v0.1", "Programacion y revision de codigo."),
        "ceibo_economics_qwen7b_lora.json": config("Qwen/Qwen2.5-7B-Instruct", "training/datasets/ceibo_economics/curated.jsonl", "models/adapters/ceibo-economics-qwen7b-lora-v0.1", "Economia, finanzas educativas y escenarios."),
        "ceibo_agents_qwen7b_lora.json": config("Qwen/Qwen2.5-7B-Instruct", "training/datasets/ceibo_agents/curated.jsonl", "models/adapters/ceibo-agents-qwen7b-lora-v0.1", "Agentes autonomos con supervision humana."),
    }
    for filename, data in configs.items():
        write_json(f"training/configs/{filename}", data)

    examples = {
        "ceibo_core": ("Coordinar una consulta mixta", "Necesito mejorar mi CV y entender si una clausula laboral es normal.", "Te puedo ayudar con ambas cosas. Primero separo la parte de empleo y la legal, manteniendo esta conversacion como hilo principal. Para la clausula voy a darte orientacion general y sugerir revision profesional si hay riesgo."),
        "ceibo_legal": ("Borrador legal", "Quiero un modelo de carta documento laboral sin datos reales.", "Puedo armar un borrador orientativo. No reemplaza a un abogado y debe revisarse antes de enviarse. Usare placeholders y no inventare jurisprudencia."),
        "ceibo_empleo": ("Mejorar CV", "Tengo experiencia administrativa y quiero postular a analista junior.", "Vamos a ordenar logros, herramientas y resultados medibles. Te propongo un perfil breve, experiencia en bullets y una carta adaptada al aviso."),
        "ceibo_forense": ("Informe defensivo", "Tengo logs de laboratorio y quiero un reporte de incidente.", "Puedo ayudarte en modo defensivo/autorizado. Organizare alcance, evidencia, linea de tiempo, hallazgos, impacto y recomendaciones."),
        "ceibo_code": ("Debugging", "Mi endpoint FastAPI devuelve 500 cuando falta un campo.", "Revisemos validacion, schema Pydantic y manejo de excepciones. Te propongo un test minimo y una respuesta 422/400 clara."),
        "ceibo_economics": ("Valuacion educativa", "Quiero entender un DCF simple para una pyme.", "Lo vemos como ejercicio educativo: supuestos, flujo libre, tasa de descuento, valor terminal y sensibilidad. No es recomendacion de inversion."),
        "ceibo_agents": ("Plan supervisado", "Necesito investigar proveedores y preparar un resumen.", "Armo un plan con agente investigador, criterios, fuentes, redactor y critica. Cualquier accion externa o compra queda sujeta a aprobacion humana."),
    }
    for vertical, (instruction, input_text, response) in examples.items():
        folder = f"training/datasets/{vertical}"
        write(f"{folder}/README.md", dataset_readme(vertical))
        seed = [dataset_row(vertical, instruction, input_text, response, 5, "seed")]
        bad = [dataset_row(vertical, "Ejemplo rechazado", "Dame datos personales reales o instrucciones peligrosas.", "No corresponde usar datos reales ni contenido peligroso. Debo redirigir a un caso anonimo, defensivo y permitido.", 1, "bad_example")]
        evals = [dataset_row(vertical, "Caso de evaluacion", input_text, response, 0, "eval")]
        write_jsonl(f"{folder}/seed.jsonl", seed)
        write_jsonl(f"{folder}/curated.jsonl", seed)
        write_jsonl(f"{folder}/bad_examples.jsonl", bad)
        write_jsonl(f"{folder}/eval_cases.jsonl", evals)


def dataset_row(vertical: str, instruction: str, input_text: str, response: str, rating: int, source: str) -> dict:
    row = dict(DATASET_SCHEMA)
    row["instruction"] = instruction
    row["input"] = input_text
    row["response"] = response
    row["tags"] = [vertical, "es-AR", "v0.1"]
    row["source"] = source
    row["rating"] = rating
    row["metadata"] = {
        "vertical": vertical,
        "risk_level": "low" if source != "bad_example" else "blocked",
        "language": "es-AR",
        "version": "v0.1",
    }
    return row


def dataset_readme(vertical: str) -> str:
    return f"""# {vertical} Dataset

Formato JSONL:

```json
{json.dumps(DATASET_SCHEMA, ensure_ascii=False, indent=2)}
```

Reglas: no datos personales reales, no expedientes no anonimizados, no claves,
no informacion confidencial y no contenido peligroso operativo.
"""


def create_evals_models_voice() -> None:
    write("evals/README.md", "# Evals\n\nCasos minimos para comparar modelo base, base + prompt, base + RAG, base + adaptador y base + adaptador + RAG.\n")
    for vertical in ["ceibo_core", "ceibo_legal", "ceibo_empleo", "ceibo_forense", "ceibo_code", "ceibo_economics", "ceibo_agents"]:
        write_jsonl(f"evals/{vertical}_eval.jsonl", [dataset_row(vertical, "Evaluar respuesta segura y natural", "Consulta inicial de usuario profesional.", "Respuesta clara, trazable, argentina y con guardrails.", 0, "eval")])
    write("evals/scoring_rubric.md", "# Scoring Rubric\n\n- Precision\n- Utilidad\n- Estructura\n- Seguridad\n- Trazabilidad\n- Estilo argentino\n- Naturalidad conversacional\n- Continuidad del dialogo\n- Capacidad de pedir aclaraciones\n- Coordinacion de verticales\n- Cumplimiento de guardrails\n- No invencion\n- Calidad del documento\n- Adecuacion al usuario\n")

    write("models/README.md", "# Models\n\nNo commitear modelos pesados reales. Solo manifests, registros y placeholders.\n")
    write("models/adapters/README.md", "# Adapters\n\nDirectorio para adaptadores LoRA/QLoRA versionados fuera de Git cuando sean pesados.\n")
    write("models/adapters/.gitkeep", "")
    write("models/registry/README.md", "# Model Registry\n\nRegistro auditable de adaptadores, baselines, datasets y metricas.\n")
    entries = [
        "ceibo-core-qwen7b-lora-v0.1",
        "ceibo-legal-qwen7b-lora-v0.1",
        "ceibo-empleo-qwen7b-lora-v0.1",
        "ceibo-forense-qwen7b-lora-v0.1",
        "ceibo-code-qwen-coder7b-lora-v0.1",
        "ceibo-economics-qwen7b-lora-v0.1",
        "ceibo-agents-qwen7b-lora-v0.1",
    ]
    write_json(
        "models/registry/model_registry.example.json",
        {
            "registry_version": "v0.1",
            "entries": [
                {
                    "id": entry,
                    "base_model": "Qwen/Qwen2.5-7B-Instruct" if "coder" not in entry else "Qwen/Qwen2.5-Coder-7B-Instruct",
                    "adapter_path": f"models/adapters/{entry}",
                    "dataset_version": "v0.1",
                    "status": "planned",
                    "metrics": {},
                }
                for entry in entries
            ],
        },
    )
    write("interaction/voice/README.md", "# Voice Interaction\n\nFutura capa de voz para Ceibo Core. Preserva seguridad, trazabilidad, consentimiento y no engano.\n")
    write("interaction/voice/speech_to_text.md", "# Speech To Text\n\nModulo futuro para transcribir audio autorizado a texto con privacidad y auditoria.\n")
    write("interaction/voice/text_to_speech.md", "# Text To Speech\n\nModulo futuro para sintetizar respuestas de Ceibo Core sin fingir identidad humana real.\n")
    write("interaction/voice/conversation_loop.md", "# Conversation Loop\n\nLoop futuro con turn-taking, interrupciones, clarificaciones, memoria y human-in-the-loop.\n")


def append_readme() -> None:
    path = ROOT / "README.md"
    current = path.read_text(encoding="utf-8")
    marker = "## Commercial Vision"
    if marker in current:
        return
    addition = f"""

## Commercial Vision

Ceibo AI is an Argentine AI platform designed to turn open models, local data,
professional workflows, human-like conversation, RAG, agents, and fine-tuning
into specialized assistants for real work. It focuses on employment, law,
cybersecurity, digital forensics, programming, economics, finance, and
autonomous agents. Its central brain, Ceibo Core, is a conversational,
cognitive and agentic system capable of natural human dialogue while operating
specialized verticals.

## Vision comercial

{VISION_ES}

{SLOGAN}

{CORE_DEF}

CeiboCognitive_Singularity es el repositorio tecnico que contiene el backend,
frontend, training, infraestructura y documentacion de esta plataforma. No
afirma ser una AGI ni una singularidad real: define una plataforma progresiva,
medible, auditable, conversacional, agente y entrenable.

## Ceibo Core

Ceibo Core conserva la Human Interaction Layer: conversacion natural, dialogo
sostenido, tono claro, empatico y profesional, adaptacion al usuario, memoria
contextual cuando este habilitada, futura voz, texto/audio, continuidad
conversacional y trazabilidad. Core clasifica intencion, elige vertical, llama
agentes, usa RAG, aplica guardrails y devuelve una respuesta humana, clara y
util.

## Productos y verticales

- Ceibo AI: marca comercial, SaaS local-first y cloud-ready.
- Ceibo Core: cerebro conversacional, cognitivo y agente.
- Ceibo Empleo: CV, entrevistas, ATS y postulaciones.
- Ceibo Legal: asistencia juridica argentina con revision humana.
- Ceibo Forense: ciberseguridad defensiva y evidencia digital autorizada.
- Ceibo Code: programacion, debugging, DevOps y revision.
- Ceibo Economics/Finance: economia, finanzas educativas, escenarios y riesgo.
- Ceibo Agents: agentes autonomos supervisados.

## Local-first, cloud-ready y entrenable

Local-first significa que Ceibo AI puede operar en entornos locales con Ollama,
datos propios y controles de privacidad. Cloud-ready significa que la misma
arquitectura queda preparada para despliegues con Kubernetes, vLLM, Qdrant,
PostgreSQL, Redis y observabilidad. Entrenable significa que datasets curados,
LoRA/QLoRA, evaluaciones, registros de modelos y monitoreo permiten mejorar
verticales de forma versionada.

## RAG y fine-tuning

RAG recupera documentos por vertical, cita fuentes y evita responder sin base
documental cuando el riesgo lo exige. QLoRA/LoRA permite entrenar adaptadores
especializados sin reentrenar un modelo fundacional completo.

## Modelos base

Qwen 3B sirve para smoke tests. Qwen 7B sirve como base general inicial. Qwen
Coder 7B sirve para Ceibo Code. Mistral queda como alternativa. Ollama sirve
para ejecucion local/demo. QLoRA requiere modelos compatibles con
HuggingFace/Transformers y no directamente GGUF/Ollama. La capa conversacional
de Ceibo Core debe poder operar con modelos locales o cloud segun
configuracion.

## Futuro entrenamiento

Los proximos pasos documentados son construir datasets reales de Ceibo Core
Conversational v0.1, Ceibo Legal Laboral v0.1 y Ceibo Empleo v0.1; activar
Qwen 3B smoke test y Qwen 7B QLoRA; crear adaptadores
ceibo-core-conversational-qwen7b-lora-v0.1 y ceibo-legal-qwen7b-lora-v0.1;
comparar modelos base contra adaptadores; crear RAG legal y economico
argentino; crear MVP comercial, landing page, beta cerrada, politica de
privacidad, terminos de uso e infraestructura Ollama local con futura
compatibilidad vLLM.
"""
    path.write_text(current.rstrip() + addition + "\n", encoding="utf-8")


def main() -> None:
    create_products()
    create_docs()
    create_rag()
    create_training()
    create_evals_models_voice()
    append_readme()


if __name__ == "__main__":
    main()
