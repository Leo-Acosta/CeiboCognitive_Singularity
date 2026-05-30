import json
from pathlib import Path

from ceibo_core.models.schemas import (
    HardwareProfile,
    ModelCandidate,
    ModelRecommendationRequest,
    TrainingPlanRequest,
    TrainingPlanResponse,
    TrainingPlanStep,
)


class ModelCatalogService:
    def __init__(self) -> None:
        self._project_root = Path(__file__).resolve().parents[4]
        self._catalog_path = self._project_root / "training" / "configs" / "base_models.json"

    def list_models(self) -> list[ModelCandidate]:
        data = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        return [ModelCandidate.model_validate(item) for item in data]

    def recommend(self, request: ModelRecommendationRequest) -> ModelCandidate:
        return self._select_model(
            use_case=request.use_case,
            hardware=request.hardware,
            prefer_quality=request.prefer_quality,
            train_from_scratch=False,
        )

    def build_training_plan(self, request: TrainingPlanRequest) -> TrainingPlanResponse:
        selected = self._select_model(
            use_case=request.use_case,
            hardware=request.hardware,
            prefer_quality=request.prefer_quality,
            train_from_scratch=request.train_from_scratch,
        )
        strategy = "pretraining_from_scratch" if request.train_from_scratch else "qlora_sft"
        output_path = f"models/{selected.model_id}-ceibo-v1"
        warnings = self._warnings(selected, request)
        return TrainingPlanResponse(
            selected_model=selected,
            strategy=strategy,
            dataset_path=request.dataset_path,
            output_model_path=output_path,
            warnings=warnings,
            steps=self._steps(selected, request, strategy, output_path),
        )

    def _select_model(
        self,
        use_case: str,
        hardware: HardwareProfile,
        prefer_quality: bool,
        train_from_scratch: bool,
    ) -> ModelCandidate:
        models = self.list_models()
        if train_from_scratch:
            return next(model for model in models if "from_scratch" in model.recommended_for)

        use_case_normalized = use_case.lower()
        candidates = [
            model
            for model in models
            if "pretraining_from_scratch" not in model.training_methods
            and model.min_vram_gb <= hardware.gpu_vram_gb
        ]
        if not candidates:
            candidates = [
                model
                for model in models
                if "pretraining_from_scratch" not in model.training_methods
                and model.min_vram_gb <= 6
            ]

        def score(model: ModelCandidate) -> tuple[int, float]:
            relevance = 0
            searchable = [*model.strengths, *model.recommended_for, model.family]
            if any(item in use_case_normalized for item in searchable):
                relevance += 4
            if use_case_normalized in model.recommended_for:
                relevance += 3
            if hardware.gpu_vram_gb >= model.preferred_vram_gb:
                relevance += 2
            if prefer_quality:
                return relevance, model.parameters_b
            return relevance, -model.parameters_b

        return max(candidates, key=score)

    def _warnings(self, selected: ModelCandidate, request: TrainingPlanRequest) -> list[str]:
        warnings: list[str] = []
        if request.train_from_scratch:
            warnings.append(
                "Entrenar desde cero un modelo competitivo requiere muchos datos y GPU; "
                "este plan crea un modelo pequeno de investigacion/educacion."
            )
        if request.hardware.gpu_vram_gb < selected.preferred_vram_gb:
            warnings.append(
                f"VRAM recomendada para {selected.model_id}: {selected.preferred_vram_gb} GB. "
                "Usa QLoRA, batch pequeno y gradient checkpointing."
            )
        warnings.append("Verifica licencia del modelo base antes de uso comercial o redistribucion.")
        return warnings

    def _steps(
        self,
        selected: ModelCandidate,
        request: TrainingPlanRequest,
        strategy: str,
        output_path: str,
    ) -> list[TrainingPlanStep]:
        if strategy == "pretraining_from_scratch":
            return [
                TrainingPlanStep(
                    order=1,
                    name="Tokenizar corpus propio",
                    description="Construir o adaptar tokenizer sobre tus documentos y conversaciones.",
                    command="python training/scripts/prepare_dataset.py training/datasets/ceibo_seed.jsonl training/datasets/ceibo_pretrain.jsonl",
                ),
                TrainingPlanStep(
                    order=2,
                    name="Entrenamiento pequeno desde cero",
                    description="Entrenar un modelo pequeno para aprendizaje y control total, no para competir con modelos fundacionales.",
                    command="python training/scripts/train_from_scratch_stub.py --config training/configs/ceibo_scratch.example.json",
                ),
                TrainingPlanStep(
                    order=3,
                    name="Evaluar y exportar",
                    description="Medir respuestas, guardar pesos y preparar runtime local.",
                ),
            ]

        return [
            TrainingPlanStep(
                order=1,
                name="Preparar dataset",
                description="Validar y normalizar ejemplos JSONL de CEIBO.",
                command=f"python training/scripts/prepare_dataset.py {request.dataset_path} training/datasets/ceibo_sft.normalized.jsonl",
            ),
            TrainingPlanStep(
                order=2,
                name="Ejecutar QLoRA/SFT",
                description=f"Fine-tuning local sobre {selected.display_name} con adapters entrenables.",
                command="python training/scripts/train_qlora_stub.py --config training/configs/ceibo_qlora.example.json",
            ),
            TrainingPlanStep(
                order=3,
                name="Fusionar o cargar adapter",
                description=f"Guardar adapter o modelo resultante en {output_path}.",
            ),
            TrainingPlanStep(
                order=4,
                name="Servir localmente",
                description=f"Exponer el modelo con {request.target_runtime} y conectar CEIBO AI Engine.",
            ),
        ]


model_catalog_service = ModelCatalogService()
