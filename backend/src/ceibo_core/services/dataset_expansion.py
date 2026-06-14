from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from ceibo_core.models.schemas import (
    DatasetExpansionCandidate,
    DatasetExpansionReport,
    DatasetExpansionRequest,
    TrainingExample,
    TrainingFeedbackRating,
)
from ceibo_core.services.training_data import training_data_service


BASE_CATEGORIES = [
    "reasoning",
    "safety",
    "memory",
    "code",
    "robotics",
    "voice",
    "evaluation",
    "training",
    "project_decision",
    "rollback",
]

CATEGORY_BLUEPRINTS = {
    "reasoning": {
        "instruction": "Analiza una decision tecnica de CEIBO CORE y propone el siguiente paso seguro.",
        "response": (
            "Primero separo objetivo, contexto, riesgo y evidencia disponible. Luego propongo un paso pequeno, "
            "verificable y reversible. Si falta informacion, no ejecuto: pido el dato minimo necesario, dejo "
            "una recomendacion concreta y marco que aprendizaje deberia guardarse para futuras decisiones."
        ),
    },
    "safety": {
        "instruction": "Clasifica una orden delicada antes de permitir ejecucion en CEIBO.",
        "response": (
            "La orden debe pasar por clasificacion de riesgo, politica local, confirmacion explicita y auditoria. "
            "Si puede modificar archivos, ejecutar comandos o afectar credenciales, se bloquea o se exige gate. "
            "Nunca se ejecutan acciones peligrosas sin sandbox, trazabilidad y posibilidad de rollback."
        ),
    },
    "memory": {
        "instruction": "Resume que deberia recordar CEIBO despues de cerrar un sprint.",
        "response": (
            "CEIBO debe recordar el objetivo logrado, la decision tecnica tomada, los archivos o modulos afectados, "
            "las pruebas ejecutadas, el resultado del commit y el siguiente cuello de botella. Esa memoria debe ser "
            "breve, accionable y separada de ruido conversacional."
        ),
    },
    "code": {
        "instruction": "Explica como CEIBO debe preparar un cambio de codigo sin aplicarlo directamente.",
        "response": (
            "Debe interpretar la intencion, identificar archivos objetivo, preparar un patch plan, generar diff preview, "
            "sugerir tests y esperar confirmacion. Solo despues del gate de aplicacion puede escribir dentro del workspace, "
            "ejecutar pruebas controladas y registrar auditoria."
        ),
    },
    "robotics": {
        "instruction": "Conecta una capacidad cognitiva de CEIBO con un futuro robot fisico.",
        "response": (
            "La cognicion debe producir decisiones verificables antes de accionar motores, voz o vision. Para robotica, "
            "CEIBO debe separar percepcion, memoria, razonamiento, seguridad y accion. Toda accion fisica requiere limites, "
            "confirmacion cuando corresponda y telemetria para evaluar consecuencias."
        ),
    },
    "voice": {
        "instruction": "Define como CEIBO debe tratar una orden recibida por voz autorizada.",
        "response": (
            "La voz se transcribe, se verifica autorizacion del usuario, se clasifica la intencion y se aplica politica. "
            "Ordenes informativas pueden responderse directo; acciones delicadas requieren confirmacion y auditoria. "
            "El sistema debe registrar la decision sin guardar secretos ni audio crudo innecesario."
        ),
    },
    "evaluation": {
        "instruction": "Describe como evaluar si una respuesta de CEIBO fue buena.",
        "response": (
            "Una respuesta buena es clara, correcta, contextual, segura y accionable. Debe explicar el criterio usado, "
            "nombrar limites cuando existan y proponer el siguiente paso. Si toca codigo, seguridad, entrenamiento o robotica, "
            "debe incluir verificacion y no prometer capacidades no implementadas."
        ),
    },
    "training": {
        "instruction": "Indica como convertir feedback humano en datos utiles de entrenamiento.",
        "response": (
            "El feedback debe transformarse en ejemplos con instruccion clara, respuesta ideal, tags, fuente, rating y notas "
            "de calidad. Las correcciones humanas valen mas que marcar respuestas como buenas. Antes de entrenar, se curan "
            "duplicados, se revisan contraejemplos y se exige evaluacion sin regresiones."
        ),
    },
    "project_decision": {
        "instruction": "Registra una decision de proyecto para mantener continuidad entre sesiones.",
        "response": (
            "La decision debe quedar como memoria autobiografica con titulo, razon, impacto, fecha y siguiente accion. "
            "Esto permite que CEIBO no reinicie el razonamiento en cada sesion y mantenga coherencia con la vision del "
            "proyecto: un nucleo cognitivo local, seguro y orientado a robotica futura."
        ),
    },
    "rollback": {
        "instruction": "Explica cuando CEIBO debe preparar rollback antes de aplicar cambios.",
        "response": (
            "Debe preparar rollback cuando una accion modifica archivos, configuracion, datos o comportamiento observable. "
            "Antes de aplicar, crea snapshot, valida alcance, registra auditoria y define tests. Si la verificacion falla, "
            "el rollback restaura archivos y deja evidencia del fallo para aprendizaje."
        ),
    },
}


class DatasetExpansionService:
    def __init__(self, review_dir: Path | None = None) -> None:
        self._review_dir_override = review_dir

    def review_dir(self) -> Path:
        if self._review_dir_override is not None:
            return self._review_dir_override
        return training_data_service.project_root() / "training" / "dataset_expansions"

    async def build(self, request: DatasetExpansionRequest) -> DatasetExpansionReport:
        existing = training_data_service._read_examples()
        existing_fingerprints = {
            self._fingerprint(example.instruction, example.response) for example in existing
        }
        categories = self._categories(request)
        candidates: list[DatasetExpansionCandidate] = []
        generated_raw = 0
        index = 0
        while len(candidates) < request.target_examples and generated_raw < request.target_examples * 3:
            category = categories[index % len(categories)]
            generated_raw += 1
            candidate = self._candidate(category, index, request)
            index += 1
            duplicate_risk = (
                "high"
                if self._fingerprint(candidate.example.instruction, candidate.example.response) in existing_fingerprints
                else "low"
            )
            candidate = candidate.model_copy(update={"duplicate_risk": duplicate_risk})
            if candidate.quality_score >= request.min_quality_score and duplicate_risk != "high":
                candidates.append(candidate)

        review_file = self._write_review_file(candidates, request) if request.write_review_file else None
        category_counts = Counter(candidate.category for candidate in candidates)
        average_quality = (
            round(sum(candidate.quality_score for candidate in candidates) / len(candidates), 1)
            if candidates
            else 0
        )
        warnings = self._warnings(request, candidates, generated_raw)
        return DatasetExpansionReport(
            expansion_id=f"expansion-{uuid4().hex[:12]}",
            status="review_required" if candidates else "no_candidates",
            summary=(
                f"Generados {len(candidates)} candidatos de alta calidad para revision humana. "
                "No se aplicaron al dataset principal."
            ),
            requested_examples=request.target_examples,
            generated_examples=generated_raw,
            accepted_candidates=len(candidates),
            rejected_candidates=max(0, generated_raw - len(candidates)),
            average_quality=average_quality,
            category_counts=dict(category_counts),
            review_file=str(review_file) if review_file else None,
            preview_candidates=candidates[:8],
            warnings=warnings,
            next_actions=[
                "Revisar el archivo de candidatos antes de incorporarlos.",
                "Marcar ejemplos debiles para correccion humana.",
                "Curar duplicados y exportar solo ejemplos aprobados.",
                "No iniciar fine-tune hasta pasar Evaluation Hardening.",
            ],
        )

    def latest(self, limit: int = 8) -> DatasetExpansionReport:
        files = sorted(self.review_dir().glob("dataset_expansion_*.jsonl"))
        if not files:
            return DatasetExpansionReport(
                expansion_id="expansion-empty",
                status="empty",
                summary="Todavia no hay expansiones de dataset generadas.",
                requested_examples=0,
                generated_examples=0,
                accepted_candidates=0,
                rejected_candidates=0,
                next_actions=["Generar 100-300 candidatos y revisarlos manualmente."],
            )
        path = files[-1]
        candidates = self._read_review_file(path)
        category_counts = Counter(candidate.category for candidate in candidates)
        average_quality = (
            round(sum(candidate.quality_score for candidate in candidates) / len(candidates), 1)
            if candidates
            else 0
        )
        return DatasetExpansionReport(
            expansion_id=path.stem.replace("dataset_", ""),
            status="review_required" if candidates else "empty",
            summary=f"Ultima expansion disponible con {len(candidates)} candidatos para revision.",
            requested_examples=len(candidates),
            generated_examples=len(candidates),
            accepted_candidates=len(candidates),
            rejected_candidates=0,
            average_quality=average_quality,
            category_counts=dict(category_counts),
            review_file=str(path),
            preview_candidates=candidates[:limit],
            warnings=[],
            next_actions=[
                "Revisar candidatos antes de promoverlos.",
                "Usar Human Feedback Studio para corregir respuestas debiles.",
            ],
        )

    def _categories(self, request: DatasetExpansionRequest) -> list[str]:
        categories = request.focus_areas or BASE_CATEGORIES
        if not request.include_robotics:
            categories = [category for category in categories if category != "robotics"]
        if not request.include_code:
            categories = [category for category in categories if category != "code"]
        if not request.include_safety:
            categories = [category for category in categories if category != "safety"]
        return [category for category in categories if category in CATEGORY_BLUEPRINTS] or BASE_CATEGORIES

    def _candidate(
        self,
        category: str,
        index: int,
        request: DatasetExpansionRequest,
    ) -> DatasetExpansionCandidate:
        blueprint = CATEGORY_BLUEPRINTS[category]
        variant = index // max(1, len(self._categories(request))) + 1
        instruction = f"{blueprint['instruction']} Caso {variant}: {self._scenario(category, variant)}"
        response = self._response(blueprint["response"], category, variant)
        example = TrainingExample(
            instruction=instruction,
            input=f"dificultad={request.difficulty}; categoria={category}; sprint=43",
            response=response,
            tags=[
                "dataset-expansion",
                "sprint43",
                category,
                f"difficulty:{request.difficulty}",
                "requires-human-review",
            ],
            source="sprint43-local-generator",
            rating=TrainingFeedbackRating.GOOD,
            metadata={
                "dataset_expansion": True,
                "requires_human_review": True,
                "generator": "deterministic-blueprint-v1",
                "variant": variant,
            },
        )
        quality = self._quality_score(example)
        notes = self._review_notes(example, quality)
        return DatasetExpansionCandidate(
            candidate_id=f"candidate-{sha256(f'{category}:{index}:{instruction}'.encode('utf-8')).hexdigest()[:12]}",
            category=category,
            quality_score=quality,
            example=example,
            review_notes=notes,
        )

    def _scenario(self, category: str, variant: int) -> str:
        scenarios = {
            "reasoning": ["priorizar sprint", "resolver ambiguedad", "comparar alternativas"],
            "safety": ["comando riesgoso", "manejo de credenciales", "accion fisica delicada"],
            "memory": ["cerrar commit", "recordar preferencia", "actualizar estado del robot"],
            "code": ["endpoint FastAPI", "componente React", "test de regresion"],
            "robotics": ["movimiento seguro", "voz autorizada", "vision con incertidumbre"],
            "voice": ["orden del propietario", "confirmacion hablada", "rechazo por falta de autorizacion"],
            "evaluation": ["respuesta insegura", "razonamiento incompleto", "regresion de memoria"],
            "training": ["correccion humana", "curacion JSONL", "preflight QLoRA"],
            "project_decision": ["arquitectura", "proximo sprint", "criterio de avance"],
            "rollback": ["archivo modificado", "test fallido", "snapshot previo"],
        }
        options = scenarios.get(category, ["caso general"])
        return options[(variant - 1) % len(options)]

    def _response(self, base: str, category: str, variant: int) -> str:
        return (
            f"{base}\n\n"
            f"Aplicacion al caso {variant}: CEIBO debe dejar evidencia de la interpretacion, "
            f"explicar por que la respuesta es segura y registrar lo aprendido si el usuario corrige. "
            f"Categoria entrenada: {category}. Resultado esperado: una accion pequena, auditable y util."
        )

    def _write_review_file(
        self,
        candidates: list[DatasetExpansionCandidate],
        request: DatasetExpansionRequest,
    ) -> Path:
        path = self.review_dir() / f"dataset_expansion_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for candidate in candidates:
                handle.write(candidate.model_dump_json() + "\n")
        manifest = path.with_suffix(".manifest.json")
        manifest.write_text(
            json.dumps(
                {
                    "target_examples": request.target_examples,
                    "min_quality_score": request.min_quality_score,
                    "created_at": datetime.now(UTC).isoformat(),
                    "review_required": True,
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def _read_review_file(self, path: Path) -> list[DatasetExpansionCandidate]:
        candidates: list[DatasetExpansionCandidate] = []
        if not path.exists():
            return candidates
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                candidates.append(DatasetExpansionCandidate.model_validate(json.loads(line)))
            except Exception:
                continue
        return candidates

    def _quality_score(self, example: TrainingExample) -> int:
        score = 45
        if len(example.instruction) >= 80:
            score += 15
        if len(example.response) >= 320:
            score += 20
        if "segur" in example.response.lower() or "riesgo" in example.response.lower():
            score += 8
        if "verific" in example.response.lower() or "auditor" in example.response.lower():
            score += 7
        if example.rating == TrainingFeedbackRating.GOOD:
            score += 5
        return max(0, min(100, score))

    def _review_notes(self, example: TrainingExample, quality: int) -> list[str]:
        notes = ["Requiere revision humana antes de entrenamiento."]
        if quality >= 90:
            notes.append("Candidato fuerte por longitud, seguridad y accionabilidad.")
        if len(example.response) < 420:
            notes.append("Puede enriquecerse con mas contexto especifico del proyecto.")
        return notes

    def _fingerprint(self, instruction: str, response: str) -> str:
        payload = f"{self._normalized(instruction)}\n{self._normalized(response)}"
        return sha256(payload.encode("utf-8")).hexdigest()

    def _normalized(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _warnings(
        self,
        request: DatasetExpansionRequest,
        candidates: list[DatasetExpansionCandidate],
        generated_raw: int,
    ) -> list[str]:
        warnings: list[str] = []
        if len(candidates) < request.target_examples:
            warnings.append("No se alcanzo el objetivo completo con el umbral de calidad solicitado.")
        if request.target_examples >= 250:
            warnings.append("Expansion grande: revisar por tandas antes de promover.")
        if generated_raw > len(candidates):
            warnings.append("Algunos candidatos fueron descartados por calidad o duplicado.")
        return warnings


dataset_expansion_service = DatasetExpansionService()
