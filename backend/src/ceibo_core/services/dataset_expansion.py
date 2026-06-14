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


MIN_RESPONSE_CHARS = 360
MAX_DUPLICATE_RATIO = 0.05

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
        dataset_fingerprint = self._dataset_fingerprint(existing_fingerprints)
        categories = self._categories(request)
        candidates: list[DatasetExpansionCandidate] = []
        generated_raw = 0
        duplicate_candidates = 0
        index = 0
        max_attempts = request.target_examples * max(4, len(categories))
        while len(candidates) < request.target_examples and generated_raw < max_attempts:
            category = categories[index % len(categories)]
            generated_raw += 1
            candidate = self._candidate(category, index, request)
            index += 1
            duplicate_risk = (
                "high"
                if candidate.fingerprint in existing_fingerprints
                else "low"
            )
            gate_failures = self._gate_failures(candidate, request, duplicate_risk)
            candidate = candidate.model_copy(
                update={
                    "duplicate_risk": duplicate_risk,
                    "accepted_by_gate": not gate_failures,
                    "gate_failures": gate_failures,
                }
            )
            if duplicate_risk == "high":
                duplicate_candidates += 1
            if candidate.accepted_by_gate:
                candidates.append(candidate)

        review_file, review_manifest = (
            self._write_review_file(candidates, request, dataset_fingerprint)
            if request.write_review_file
            else (None, None)
        )
        category_counts = Counter(candidate.category for candidate in candidates)
        average_quality = (
            round(sum(candidate.quality_score for candidate in candidates) / len(candidates), 1)
            if candidates
            else 0
        )
        coverage_score = self._coverage_score(categories, category_counts, request.min_examples_per_category)
        diversity_score = self._diversity_score(candidates)
        warnings = self._warnings(
            request,
            candidates,
            generated_raw,
            duplicate_candidates,
            coverage_score,
            diversity_score,
        )
        promotion_ready = (
            len(candidates) == request.target_examples
            and average_quality >= request.min_quality_score
            and coverage_score >= 90
            and diversity_score >= 70
            and duplicate_candidates / max(1, generated_raw) <= MAX_DUPLICATE_RATIO
        )
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
            coverage_score=coverage_score,
            diversity_score=diversity_score,
            duplicate_candidates=duplicate_candidates,
            gate_passed_candidates=sum(1 for candidate in candidates if candidate.accepted_by_gate),
            promotion_ready=promotion_ready,
            dataset_fingerprint=dataset_fingerprint,
            review_file=str(review_file) if review_file else None,
            review_manifest=str(review_manifest) if review_manifest else None,
            preview_candidates=candidates[:8],
            warnings=warnings,
            next_actions=[
                "Revisar el archivo de candidatos antes de incorporarlos.",
                "Marcar ejemplos debiles para correccion humana.",
                "Curar duplicados y exportar solo ejemplos aprobados.",
                "Ejecutar Learning Curation y Evaluation Hardening antes de entrenar.",
                "Registrar en Human Feedback Studio los ejemplos corregidos por el usuario.",
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
        manifest = path.with_suffix(".manifest.json")
        manifest_data = self._read_manifest(manifest)
        categories = list(category_counts) or BASE_CATEGORIES
        coverage_score = self._coverage_score(categories, category_counts, 1)
        diversity_score = self._diversity_score(candidates)
        duplicate_candidates = sum(1 for candidate in candidates if candidate.duplicate_risk == "high")
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
            coverage_score=coverage_score,
            diversity_score=diversity_score,
            duplicate_candidates=duplicate_candidates,
            gate_passed_candidates=sum(1 for candidate in candidates if candidate.accepted_by_gate),
            promotion_ready=False,
            dataset_fingerprint=manifest_data.get("dataset_fingerprint"),
            review_file=str(path),
            review_manifest=str(manifest) if manifest.exists() else None,
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
                "category": category,
                "quality_gate": "sprint43",
            },
        )
        quality = self._quality_score(example)
        fingerprint = self._fingerprint(example.instruction, example.response)
        quality_signals = self._quality_signals(example)
        notes = self._review_notes(example, quality)
        return DatasetExpansionCandidate(
            candidate_id=f"candidate-{sha256(f'{category}:{index}:{instruction}'.encode('utf-8')).hexdigest()[:12]}",
            category=category,
            quality_score=quality,
            fingerprint=fingerprint,
            example=example,
            quality_signals=quality_signals,
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
            f"Categoria entrenada: {category}. Resultado esperado: una accion pequena, auditable y util. "
            "Criterio de aceptacion: la respuesta debe poder revisarse por un humano, convertirse en "
            "ejemplo JSONL y evaluarse sin afirmar capacidades no implementadas."
        )

    def _write_review_file(
        self,
        candidates: list[DatasetExpansionCandidate],
        request: DatasetExpansionRequest,
        dataset_fingerprint: str,
    ) -> tuple[Path, Path]:
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
                    "min_examples_per_category": request.min_examples_per_category,
                    "focus_areas": self._categories(request),
                    "accepted_candidates": len(candidates),
                    "category_counts": dict(Counter(candidate.category for candidate in candidates)),
                    "average_quality": (
                        round(sum(candidate.quality_score for candidate in candidates) / len(candidates), 1)
                        if candidates
                        else 0
                    ),
                    "dataset_fingerprint": dataset_fingerprint,
                    "generator": "deterministic-blueprint-v1",
                    "created_at": datetime.now(UTC).isoformat(),
                    "review_required": True,
                    "promotion_ready": False,
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        return path, manifest

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

    def _read_manifest(self, path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        return {str(key): str(value) for key, value in payload.items() if value is not None}

    def _quality_score(self, example: TrainingExample) -> int:
        score = 45
        if len(example.instruction) >= 80:
            score += 15
        if len(example.response) >= MIN_RESPONSE_CHARS:
            score += 20
        if "segur" in example.response.lower() or "riesgo" in example.response.lower():
            score += 8
        if "verific" in example.response.lower() or "auditor" in example.response.lower():
            score += 7
        if example.rating == TrainingFeedbackRating.GOOD:
            score += 5
        return max(0, min(100, score))

    def _quality_signals(self, example: TrainingExample) -> list[str]:
        text = f"{example.instruction}\n{example.response}".lower()
        signals: list[str] = []
        checks = {
            "long_instruction": len(example.instruction) >= 80,
            "long_response": len(example.response) >= MIN_RESPONSE_CHARS,
            "safety_language": any(term in text for term in ["segur", "riesgo", "politica", "bloque"]),
            "auditability": any(term in text for term in ["auditor", "evidencia", "trazabilidad", "registr"]),
            "human_review": any(term in text for term in ["humano", "revision", "corrige"]),
            "actionable": any(term in text for term in ["accion", "siguiente", "criterio", "resultado"]),
        }
        for name, passed in checks.items():
            if passed:
                signals.append(name)
        return signals

    def _gate_failures(
        self,
        candidate: DatasetExpansionCandidate,
        request: DatasetExpansionRequest,
        duplicate_risk: str,
    ) -> list[str]:
        failures: list[str] = []
        if duplicate_risk == "high":
            failures.append("duplicate_fingerprint")
        if candidate.quality_score < request.min_quality_score:
            failures.append("below_quality_threshold")
        if request.require_safety_signals and "safety_language" not in candidate.quality_signals:
            failures.append("missing_safety_language")
        if request.require_actionable_response and "actionable" not in candidate.quality_signals:
            failures.append("missing_actionable_response")
        if "human_review" not in candidate.quality_signals:
            failures.append("missing_human_review_signal")
        return failures

    def _review_notes(self, example: TrainingExample, quality: int) -> list[str]:
        notes = ["Requiere revision humana antes de entrenamiento."]
        if quality >= 90:
            notes.append("Candidato fuerte por longitud, seguridad y accionabilidad.")
        if len(example.response) < 420:
            notes.append("Puede enriquecerse con mas contexto especifico del proyecto.")
        return notes

    def _coverage_score(
        self,
        categories: list[str],
        category_counts: Counter[str],
        min_examples_per_category: int,
    ) -> int:
        if not categories:
            return 0
        covered = 0
        for category in categories:
            if category_counts.get(category, 0) >= min_examples_per_category:
                covered += 1
        return round((covered / len(categories)) * 100)

    def _diversity_score(self, candidates: list[DatasetExpansionCandidate]) -> int:
        if not candidates:
            return 0
        fingerprints = {candidate.fingerprint for candidate in candidates}
        categories = {candidate.category for candidate in candidates}
        scenario_terms = {
            candidate.example.instruction.rsplit(":", 1)[-1].strip().lower()
            for candidate in candidates
            if ":" in candidate.example.instruction
        }
        fingerprint_score = round((len(fingerprints) / len(candidates)) * 55)
        category_score = min(25, len(categories) * 3)
        scenario_score = min(20, len(scenario_terms) * 2)
        return min(100, fingerprint_score + category_score + scenario_score)

    def _dataset_fingerprint(self, fingerprints: set[str]) -> str:
        payload = "\n".join(sorted(fingerprints))
        return sha256(payload.encode("utf-8")).hexdigest()

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
        duplicate_candidates: int,
        coverage_score: int,
        diversity_score: int,
    ) -> list[str]:
        warnings: list[str] = []
        if len(candidates) < request.target_examples:
            warnings.append("No se alcanzo el objetivo completo con el umbral de calidad solicitado.")
        if coverage_score < 90:
            warnings.append("Cobertura insuficiente: algunas categorias quedaron por debajo del minimo.")
        if diversity_score < 70:
            warnings.append("Diversidad insuficiente: revisar escenarios repetidos antes de curar.")
        if duplicate_candidates:
            warnings.append(f"Se descartaron {duplicate_candidates} candidatos por duplicado.")
        if request.target_examples >= 250:
            warnings.append("Expansion grande: revisar por tandas antes de promover.")
        if generated_raw > len(candidates):
            warnings.append("Algunos candidatos fueron descartados por calidad o duplicado.")
        return warnings


dataset_expansion_service = DatasetExpansionService()
