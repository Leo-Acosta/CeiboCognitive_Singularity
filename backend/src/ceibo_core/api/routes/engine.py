from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    DatasetVersionRecord,
    DatasetVersionRequest,
    EngineGenerateRequest,
    EngineGenerateResponse,
    EngineStatus,
    EvaluationSuiteReport,
    DatasetCurationReport,
    DatasetCurationRequest,
    ModelCandidate,
    ModelRecommendationRequest,
    ModelVersionRecord,
    ModelVersionRequest,
    QloraTrainingRequest,
    RegistryOverview,
    TeacherReviewRequest,
    TeacherReviewResponse,
    TeacherStatus,
    TeacherSyntheticRequest,
    TeacherSyntheticResponse,
    TrainingDatasetStats,
    TrainingExample,
    TrainingExampleRequest,
    TrainingFeedbackRating,
    TrainingFeedbackRequest,
    TrainingPlanRequest,
    TrainingPlanResponse,
    TrainingRunnerReport,
)
from ceibo_core.services.dataset_curator import dataset_curator_service
from ceibo_core.services.evaluation_harness import evaluation_harness_service
from ceibo_core.services.model_catalog import model_catalog_service
from ceibo_core.services.model_registry import model_registry_service
from ceibo_core.services.teacher_agent import teacher_agent_service
from ceibo_core.services.training_data import training_data_service
from ceibo_core.services.training_runner import training_runner_service

router = APIRouter(prefix="/engine", tags=["engine"])


@router.get("/status", response_model=EngineStatus)
async def engine_status() -> EngineStatus:
    return ceibo_engine.status()


@router.post("/evaluations/run", response_model=EvaluationSuiteReport)
async def run_evaluation_suite() -> EvaluationSuiteReport:
    return await evaluation_harness_service.run()


@router.get("/evaluations/latest", response_model=EvaluationSuiteReport | None)
async def latest_evaluation_suite() -> EvaluationSuiteReport | None:
    return evaluation_harness_service.latest()


@router.post("/generate", response_model=EngineGenerateResponse)
async def generate(request: EngineGenerateRequest) -> EngineGenerateResponse:
    return await ceibo_engine.generate(
        system_prompt=request.system_prompt,
        user_message=request.message,
        context=request.context,
    )


@router.get("/models", response_model=list[ModelCandidate])
async def list_models() -> list[ModelCandidate]:
    return model_catalog_service.list_models()


@router.get("/registry", response_model=RegistryOverview)
async def registry_overview(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> RegistryOverview:
    return await model_registry_service.overview(db, limit=limit)


@router.post("/registry/bootstrap", response_model=RegistryOverview)
async def bootstrap_registry(db: AsyncSession = Depends(get_db)) -> RegistryOverview:
    return await model_registry_service.bootstrap_seed_registry(db)


@router.get("/registry/datasets", response_model=list[DatasetVersionRecord])
async def list_dataset_versions(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[DatasetVersionRecord]:
    return await model_registry_service.list_datasets(db, limit=limit)


@router.post("/registry/datasets", response_model=DatasetVersionRecord)
async def register_dataset_version(
    request: DatasetVersionRequest,
    db: AsyncSession = Depends(get_db),
) -> DatasetVersionRecord:
    try:
        return await model_registry_service.register_dataset(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/registry/models", response_model=list[ModelVersionRecord])
async def list_model_versions(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[ModelVersionRecord]:
    return await model_registry_service.list_models(db, limit=limit)


@router.post("/registry/models", response_model=ModelVersionRecord)
async def register_model_version(
    request: ModelVersionRequest,
    db: AsyncSession = Depends(get_db),
) -> ModelVersionRecord:
    return await model_registry_service.register_model(db, request)


@router.post("/models/recommend", response_model=ModelCandidate)
async def recommend_model(request: ModelRecommendationRequest) -> ModelCandidate:
    return model_catalog_service.recommend(request)


@router.post("/training/plan", response_model=TrainingPlanResponse)
async def training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    return model_catalog_service.build_training_plan(request)


@router.get("/training/examples", response_model=list[TrainingExample])
async def list_training_examples(limit: int = 20) -> list[TrainingExample]:
    return await training_data_service.list_examples(limit=limit)


@router.post("/training/examples", response_model=TrainingExample)
async def append_training_example(request: TrainingExampleRequest) -> TrainingExample:
    return await training_data_service.append_example(request)


@router.post("/training/feedback", response_model=TrainingExample)
async def append_training_feedback(request: TrainingFeedbackRequest) -> TrainingExample:
    return await training_data_service.append_feedback(request)


@router.get("/training/stats", response_model=TrainingDatasetStats)
async def training_dataset_stats() -> TrainingDatasetStats:
    return await training_data_service.stats()


@router.post("/training/curate/preview", response_model=DatasetCurationReport)
async def preview_training_dataset_curation(
    request: DatasetCurationRequest,
) -> DatasetCurationReport:
    try:
        return dataset_curator_service.curate(request, write_output=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/training/curate/export", response_model=DatasetCurationReport)
async def export_training_dataset_curation(
    request: DatasetCurationRequest,
) -> DatasetCurationReport:
    try:
        return dataset_curator_service.curate(request, write_output=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/teacher/status", response_model=TeacherStatus)
async def teacher_status() -> TeacherStatus:
    return await teacher_agent_service.status()


@router.post("/teacher/review", response_model=TeacherReviewResponse)
async def teacher_review(request: TeacherReviewRequest) -> TeacherReviewResponse:
    try:
        review = await teacher_agent_service.review_response(request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Teacher IA unavailable: {exc}") from exc

    if not request.save_to_dataset:
        return review

    saved_example = await training_data_service.append_feedback(
        TrainingFeedbackRequest(
            instruction=request.prompt,
            original_response=request.ceibo_response,
            corrected_response=review.ideal_response,
            rating=TrainingFeedbackRating.CORRECTED,
            tags=["teacher", "ollama", "mistral", request.category],
            source="ollama-mistral-teacher",
            metadata={
                "teacher_score": review.score,
                "teacher_passed": review.passed,
                "teacher_issues": review.issues,
                "teacher_strengths": review.strengths,
                "teacher_model": review.teacher_model,
            },
        )
    )
    return review.model_copy(update={"saved_example": saved_example})


@router.post("/teacher/synthetic-examples", response_model=TeacherSyntheticResponse)
async def teacher_synthetic_examples(
    request: TeacherSyntheticRequest,
) -> TeacherSyntheticResponse:
    try:
        result = await teacher_agent_service.generate_synthetic_examples(request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Teacher IA unavailable: {exc}") from exc

    if not request.save_to_dataset:
        return result

    saved_examples: list[TrainingExample] = []
    for example in result.examples:
        saved_examples.append(
            await training_data_service.append_example(
                TrainingExampleRequest(
                    instruction=example.instruction,
                    input=example.input,
                    response=example.response,
                    tags=example.tags,
                    source=example.source,
                    metadata=example.metadata,
                )
            )
        )
    return result.model_copy(
        update={
            "examples": saved_examples,
            "saved_count": len(saved_examples),
        }
    )


@router.post("/training/qlora/preflight", response_model=TrainingRunnerReport)
async def qlora_preflight(request: QloraTrainingRequest) -> TrainingRunnerReport:
    try:
        return training_runner_service.preflight(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/training/qlora/start", response_model=TrainingRunnerReport)
async def qlora_start(request: QloraTrainingRequest) -> TrainingRunnerReport:
    try:
        return training_runner_service.start(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/training/qlora/jobs", response_model=list[TrainingRunnerReport])
async def qlora_jobs(limit: int = 20) -> list[TrainingRunnerReport]:
    return training_runner_service.list_runs(limit=limit)


@router.get("/training/qlora/jobs/{run_id}", response_model=TrainingRunnerReport)
async def qlora_job(run_id: str) -> TrainingRunnerReport:
    try:
        return training_runner_service.get_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
