from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CEIBO CORE"
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    embeddings_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://ollama:11434"
    teacher_provider: str = "ollama"
    teacher_base_url: str = "http://127.0.0.1:11434"
    teacher_model: str = "mistral:latest"
    teacher_timeout_seconds: int = 600
    default_llm_provider: str = "ceibo_local"
    ceibo_engine_model_id: str = "ceibo-core-local-v0"
    ceibo_engine_mode: str = "rules+rag"
    ceibo_training_dataset_path: str = "training/datasets/ceibo_instructions.jsonl"
    ceibo_evaluation_report_path: str = "training/evaluations/latest_report.json"
    ceibo_core_directive: str = (
        "Ayudar y ensenar a su usuario principal, facilitando cada requerimiento "
        "con respuestas claras, utiles, accionables y adaptadas a lo que necesite."
    )

    database_url: str = "postgresql+asyncpg://ceibo:ceibo_dev_password@postgres:5432/ceibo_core"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"
    nats_url: str = "nats://nats:4222"
    persistence_enabled: bool = False
    event_bus_enabled: bool = False
    memory_vector_enabled: bool = False
    memory_collection_name: str = "ceibo_memories"
    memory_embedding_dimensions: int = 384
    memory_local_limit: int = 500

    jwt_secret: str = Field(default="change-me-in-production", min_length=16)
    jwt_issuer: str = "ceibo-core"
    access_token_minutes: int = 60
    rbac_enforced: bool = False
    local_dev_admin_enabled: bool = True

    enable_system_control: bool = False
    enable_desktop_automation: bool = False
    sandbox_workdir: str = "/workspace/sandbox"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
