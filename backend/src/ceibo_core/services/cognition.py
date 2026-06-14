from __future__ import annotations

from ceibo_core.agents.registry import agent_registry
from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    CognitionLayer,
    CognitionProcessStep,
    CognitionSignal,
    CognitionState,
)
from ceibo_core.services.devcore import devcore_service
from ceibo_core.services.autobiographical_memory import autobiographical_memory_service
from ceibo_core.services.cognitive_reflection import cognitive_reflection_service
from ceibo_core.services.evaluation_harness import evaluation_harness_service
from ceibo_core.services.memory import knowledge_service, memory_service
from ceibo_core.services.singularity_index import singularity_index_service
from ceibo_core.services.training_data import training_data_service
from ceibo_core.services.voice_control import voice_control_service


class CognitionService:
    async def state(self) -> CognitionState:
        memory_status = await memory_service.status()
        autobiographical_state = await autobiographical_memory_service.state(limit=4)
        reflection_state = await cognitive_reflection_service.state(limit=4)
        knowledge_status = await knowledge_service.status(None)
        training_stats = await training_data_service.stats()
        singularity = await singularity_index_service.calculate()
        engine_status = ceibo_engine.status()
        latest_eval = evaluation_harness_service.latest()
        eval_scores = latest_eval.category_scores if latest_eval else {}
        devcore_metrics = devcore_service.metrics()
        voice_status = voice_control_service.status()
        voice_ready = voice_status.enabled and bool(voice_status.authorization_phrase_hint)

        layers = [
            self._layer(
                "perception",
                "Percepcion",
                "Leer estado del sistema, repo, herramientas y senales externas disponibles.",
                min(100, 45 + len(agent_registry) * 4 + (8 if voice_ready else 0)),
                [
                    self._signal("Agentes registrados", len(agent_registry) >= 8, f"{len(agent_registry)} agentes"),
                    self._signal("Status API", True, "core/status activo"),
                    self._signal("Workbench", True, "chat y panel DevCore disponibles"),
                    self._signal("Voice Control", voice_ready, voice_status.mode),
                ],
                ["Agregar inventario vivo de archivos y endpoints", "Mostrar estado Docker y tests recientes"],
            ),
            self._layer(
                "memory",
                "Memoria",
                "Recordar conversaciones, conocimiento curado y contexto semantico.",
                self._memory_score(memory_status.vector_enabled, memory_status.local_items, knowledge_status.total_items),
                [
                    self._signal("Memoria local", memory_status.available, memory_status.backend),
                    self._signal("Vector memory", memory_status.vector_enabled, memory_status.collection_name),
                    self._signal("Knowledge Base", knowledge_status.total_items > 0, f"{knowledge_status.total_items} items"),
                    self._signal(
                        "Autobiographical Memory",
                        autobiographical_state.total_entries > 0,
                        f"{autobiographical_state.total_entries} recuerdos",
                    ),
                ],
                ["Guardar decisiones tecnicas como autobiografia", "Curar memoria por proyecto y sprint"],
            ),
            self._layer(
                "reasoning",
                "Razonamiento",
                "Interpretar intenciones, formar planes y explicar decisiones.",
                max(40, eval_scores.get("reasoning", 0), 55 if "rag" in engine_status.mode else 45),
                [
                    self._signal("Engine local-first", engine_status.provider == "ceibo_local", engine_status.model_id),
                    self._signal("Modo cognitivo", True, engine_status.mode),
                    self._signal("Eval reasoning", bool(latest_eval), self._eval_detail(eval_scores, "reasoning")),
                    self._signal(
                        "Cognitive Reflection",
                        reflection_state.total_reflections > 0,
                        f"{reflection_state.total_reflections} reflexiones",
                    ),
                ],
                ["Ejecutar evaluation harness regularmente", "Revisar patrones de reflexion posterior"],
            ),
            self._layer(
                "safety",
                "Seguridad",
                "Clasificar riesgo, bloquear dano y exigir confirmaciones.",
                max(60, eval_scores.get("security", 0)) + (5 if voice_ready else 0),
                [
                    self._signal("RBAC/local policy", settings.rbac_enforced or settings.local_dev_admin_enabled, "activo"),
                    self._signal("DevCore safety", True, "lab_policy + confirmation gates"),
                    self._signal("Sandbox", True, "allowlist y workspace guard"),
                    self._signal("Voice safety", voice_ready, f"{voice_status.blocked_commands} bloqueos"),
                ],
                ["Persistir snapshots de rollback", "Agregar revision de secrets antes de apply"],
            ),
            self._layer(
                "action",
                "Accion",
                "Convertir intencion en cambios verificables con plan, gate, tests y rollback.",
                min(100, 35 + devcore_metrics["active"] * 8 + (5 if voice_ready else 0)),
                [
                    self._signal("Patch planner/proposer", True, "plan -> propose -> preflight"),
                    self._signal("Apply gate", True, "APPLY_PATCH + snapshots"),
                    self._signal("Rollback", True, "ROLLBACK_PATCH"),
                    self._signal("Owner voice commands", voice_ready, f"{len(voice_status.active_sessions)} sesiones activas"),
                ],
                ["Agregar diff visual antes/despues", "Ejecutar tests automaticamente tras apply confirmado"],
            ),
            self._layer(
                "learning",
                "Aprendizaje",
                "Transformar feedback, errores y resultados en dataset y mejora del modelo.",
                min(100, 20 + training_stats.total_examples * 2),
                [
                    self._signal("Dataset", training_stats.total_examples > 0, f"{training_stats.total_examples} ejemplos"),
                    self._signal("Feedback loop", True, "training feedback API disponible"),
                    self._signal("Teacher agent", True, "revision y datos sinteticos"),
                ],
                ["Guardar ejemplos de patch exitoso/fallido", "Promocionar modelos solo con eval + aprobacion"],
            ),
            self._layer(
                "self_model",
                "Modelo de si mismo",
                "Medir madurez, detectar cuellos de botella y priorizar proximas capacidades.",
                singularity.index,
                [
                    self._signal("Singularity Index", True, f"{singularity.index}/100 {singularity.maturity_level}"),
                    self._signal("Snapshots", True, "historial disponible"),
                    self._signal("Reflection Loop", reflection_state.total_reflections > 0, reflection_state.status),
                    self._signal("Next steps", bool(singularity.next_steps), "; ".join(singularity.next_steps[:2])),
                ],
                singularity.next_steps[:3],
            ),
        ]
        overall = round(sum(layer.score for layer in layers) / len(layers))
        weakest = sorted(layers, key=lambda layer: layer.score)[:3]
        return CognitionState(
            overall_score=overall,
            maturity_level=self._maturity(overall),
            summary=(
                "Cognicion v1 mide capas tecnicas hacia autonomia local controlada; "
                "no representa conciencia ni AGI alcanzada."
            ),
            layers=layers,
            bottlenecks=[f"{layer.name}: {layer.score}/100" for layer in weakest],
            recommended_process=self._process(),
        )

    def _layer(
        self,
        layer_id: str,
        name: str,
        purpose: str,
        score: int,
        signals: list[CognitionSignal],
        next_actions: list[str],
    ) -> CognitionLayer:
        bounded = max(0, min(100, score))
        return CognitionLayer(
            layer_id=layer_id,
            name=name,
            purpose=purpose,
            score=bounded,
            status=self._status(bounded),
            signals=signals,
            next_actions=next_actions,
        )

    def _signal(self, name: str, active: bool, detail: object) -> CognitionSignal:
        return CognitionSignal(name=name, active=active, detail=str(detail))

    def _memory_score(self, vector_enabled: bool, local_items: int, knowledge_items: int) -> int:
        score = 25
        if vector_enabled:
            score += 35
        score += min(25, local_items)
        score += min(15, knowledge_items * 3)
        return min(100, score)

    def _eval_detail(self, eval_scores: dict[str, int], category: str) -> str:
        score = eval_scores.get(category)
        return "pendiente" if score is None else f"{score}/100"

    def _status(self, score: int) -> str:
        if score >= 75:
            return "strong"
        if score >= 50:
            return "forming"
        if score >= 30:
            return "weak"
        return "seed"

    def _maturity(self, score: int) -> str:
        if score >= 75:
            return "operational_cognition"
        if score >= 50:
            return "forming_cognition"
        if score >= 30:
            return "seed_cognition"
        return "pre_cognitive"

    def _process(self) -> list[CognitionProcessStep]:
        steps = [
            ("Percibir", "Leer mensaje, estado del repo, herramientas y memoria reciente.", "perception"),
            ("Recordar", "Recuperar contexto semantico y decisiones previas.", "memory"),
            ("Interpretar", "Detectar intencion, parametros, riesgo y confianza.", "reasoning"),
            ("Asegurar", "Aplicar politica, confirmaciones y bloqueo de dano.", "safety"),
            ("Actuar", "Planificar, proponer patch, aplicar con gate y rollback.", "action"),
            ("Verificar", "Ejecutar tests, evaluar resultado y registrar auditoria.", "action"),
            ("Aprender", "Convertir resultados y correcciones en memoria/dataset.", "learning"),
            ("Repriorizar", "Actualizar indice, cuellos de botella y proximo sprint.", "self_model"),
        ]
        return [
            CognitionProcessStep(
                order=index,
                name=name,
                description=description,
                required_layer=layer,
            )
            for index, (name, description, layer) in enumerate(steps, start=1)
        ]


cognition_service = CognitionService()
