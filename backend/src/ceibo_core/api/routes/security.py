from __future__ import annotations

from fastapi import APIRouter

from fastapi import APIRouter, Body, HTTPException

import structlog

from ceibo_core.core.config import settings
from ceibo_core.security.ollama_guard import ollama_status, validate_ollama_base_url, UnsafeOllamaHostError

logger = structlog.get_logger()

router = APIRouter()


@router.get("/security/ollama-status")
async def get_ollama_status():
    try:
        status = ollama_status(settings.ollama_base_url)
        # include minimal config flags relevant to UI
        status.update({
            "default_llm_provider": settings.default_llm_provider,
            "ollama_chat_model": settings.ollama_chat_model,
            "block_non_local_ollama": settings.block_non_local_ollama,
        })
        return status
    except Exception as exc:  # pragma: no cover - ensure endpoint never returns 500
        logger.error("ollama_status_failure", error=str(exc))
        # Return a controlled JSON response (do not expose internals)
        return {
            "ollama_base_url": getattr(settings, "ollama_base_url", None),
            "is_localhost": False,
            "safe": False,
            "message": "Error al obtener el estado de Ollama. Revisa los logs del servidor.",
            "default_llm_provider": settings.default_llm_provider,
            "ollama_chat_model": getattr(settings, "ollama_chat_model", None),
            "block_non_local_ollama": settings.block_non_local_ollama,
        }


@router.post("/security/set-model")
async def set_model(payload: dict = Body(...)):
    model = payload.get("model")
    allowed = ["qwen3:8b", "qwen3:14b", "mistral", "llama3.1:8b", "gemma3"]
    if model not in allowed:
        raise HTTPException(status_code=400, detail="Modelo no soportado")
    settings.ollama_chat_model = model
    settings.default_llm_provider = "ollama"
    return {"ok": True, "ollama_chat_model": settings.ollama_chat_model}


@router.post("/security/set-ollama-url")
async def set_ollama_url(payload: dict = Body(...)):
    url = payload.get("ollama_base_url")
    if not url:
        raise HTTPException(status_code=400, detail="ollama_base_url es requerido")
    # If blocking non-local hosts, validate
    if settings.block_non_local_ollama:
        try:
            validate_ollama_base_url(url)
        except UnsafeOllamaHostError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    # Accept the URL
    settings.ollama_base_url = url
    return {"ok": True, "ollama_base_url": settings.ollama_base_url}
