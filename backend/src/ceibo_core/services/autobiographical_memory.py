from __future__ import annotations

import json
import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    AutobiographicalMemoryEntry,
    AutobiographicalMemoryRequest,
    AutobiographicalMemoryState,
)
from ceibo_core.services.memory import sanitize_memory_text
from ceibo_core.services.training_data import training_data_service


DEFAULT_SEED_MEMORIES = [
    {
        "kind": "goal",
        "title": "Construir CEIBO como nucleo cognitivo local",
        "content": (
            "El objetivo principal del proyecto es evolucionar CEIBO CORE como cerebro logico "
            "y de discernimiento para un futuro robot con voz, vision, movimiento y toma de decisiones."
        ),
        "importance": 95,
        "tags": ["ceibo", "robot", "cognition", "long-term-goal"],
    },
    {
        "kind": "preference",
        "title": "Trabajar en sprints robustos y verificables",
        "content": (
            "El usuario prefiere avanzar por sprints, cerrar ciclos con tests, commit y push, "
            "y mantener controles de seguridad antes de ejecucion real."
        ),
        "importance": 90,
        "tags": ["workflow", "sprints", "verification"],
    },
    {
        "kind": "decision",
        "title": "Autonomia controlada antes que ejecucion libre",
        "content": (
            "CEIBO debe interpretar, clasificar riesgo, pedir confirmacion, ejecutar en sandbox, "
            "auditar y permitir rollback antes de aplicar acciones delicadas."
        ),
        "importance": 92,
        "tags": ["safety", "devcore", "execution-gate"],
    },
    {
        "kind": "project_state",
        "title": "Sprint 41 habilita memoria autobiografica",
        "content": (
            "El proyecto ya tiene Workbench, parser DevCore, safety layer, sandbox, patch gates, "
            "feedback humano, learning loop, evaluaciones y evidencia de entrenamiento."
        ),
        "importance": 85,
        "tags": ["sprint41", "project-state", "memory"],
    },
]


class AutobiographicalMemoryService:
    def __init__(self, path: Path | None = None) -> None:
        self._path_override = path

    def memory_path(self) -> Path:
        if self._path_override is not None:
            return self._path_override
        configured = Path(settings.ceibo_autobiographical_memory_path)
        if configured.is_absolute():
            return configured
        return training_data_service.project_root() / configured

    async def state(self, limit: int = 8) -> AutobiographicalMemoryState:
        entries = self._read_entries()
        sorted_entries = sorted(
            entries,
            key=lambda item: (item.importance, item.updated_at or item.created_at),
            reverse=True,
        )
        return self._state(entries=entries, recent=sorted_entries[:limit])

    async def remember(self, request: AutobiographicalMemoryRequest) -> AutobiographicalMemoryState:
        entries = self._read_entries()
        entry = self._entry_from_request(request)
        entries = self._upsert(entries, entry)
        self._write_entries(entries)
        sorted_entries = sorted(entries, key=lambda item: item.created_at, reverse=True)
        return self._state(entries=entries, recent=sorted_entries[:8], saved_entry=entry)

    async def bootstrap(self) -> AutobiographicalMemoryState:
        entries = self._read_entries()
        saved: AutobiographicalMemoryEntry | None = None
        for seed in DEFAULT_SEED_MEMORIES:
            entry = self._entry_from_request(AutobiographicalMemoryRequest(**seed), source="sprint41_seed")
            before = len(entries)
            entries = self._upsert(entries, entry)
            if len(entries) > before:
                saved = entry
        self._write_entries(entries)
        sorted_entries = sorted(entries, key=lambda item: item.created_at, reverse=True)
        return self._state(entries=entries, recent=sorted_entries[:8], saved_entry=saved)

    async def context_for(self, query: str, limit: int = 5) -> list[str]:
        entries = self._read_entries()
        if not entries:
            return []
        query_terms = self._terms(query)
        scored: list[tuple[int, AutobiographicalMemoryEntry]] = []
        for entry in entries:
            text_terms = self._terms(f"{entry.kind} {entry.title} {entry.content} {' '.join(entry.tags)}")
            overlap = len(query_terms & text_terms)
            score = overlap * 12 + entry.importance
            if overlap or entry.importance >= 90:
                scored.append((score, entry))
        scored.sort(key=lambda item: (item[0], item[1].updated_at or item[1].created_at), reverse=True)
        return [self._context_line(entry) for _, entry in scored[:limit]]

    def _entry_from_request(
        self,
        request: AutobiographicalMemoryRequest,
        source: str | None = None,
    ) -> AutobiographicalMemoryEntry:
        title, title_redacted = sanitize_memory_text(request.title)
        content, content_redacted = sanitize_memory_text(request.content)
        metadata = {**request.metadata}
        if title_redacted or content_redacted:
            metadata["redacted"] = True
        now = datetime.now(UTC)
        return AutobiographicalMemoryEntry(
            memory_id=self._stable_id(request.kind, title, content),
            kind=request.kind,
            title=title,
            content=content,
            importance=request.importance,
            source=source or request.source,
            tags=self._normalize_tags(request.tags),
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )

    def _read_entries(self) -> list[AutobiographicalMemoryEntry]:
        path = self.memory_path()
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        records = raw.get("entries", raw if isinstance(raw, list) else [])
        entries: list[AutobiographicalMemoryEntry] = []
        for record in records:
            try:
                entries.append(AutobiographicalMemoryEntry.model_validate(record))
            except Exception:
                continue
        return entries

    def _write_entries(self, entries: list[AutobiographicalMemoryEntry]) -> None:
        path = self.memory_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "entries": [entry.model_dump(mode="json") for entry in entries],
        }
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _upsert(
        self,
        entries: list[AutobiographicalMemoryEntry],
        candidate: AutobiographicalMemoryEntry,
    ) -> list[AutobiographicalMemoryEntry]:
        merged: list[AutobiographicalMemoryEntry] = []
        replaced = False
        for entry in entries:
            same_id = entry.memory_id == candidate.memory_id
            same_title = entry.kind == candidate.kind and entry.title.lower() == candidate.title.lower()
            if same_id or same_title:
                merged_tags = self._normalize_tags([*entry.tags, *candidate.tags])
                if (
                    entry.content == candidate.content
                    and entry.importance == candidate.importance
                    and entry.source == candidate.source
                    and entry.tags == merged_tags
                    and entry.metadata == {**entry.metadata, **candidate.metadata}
                ):
                    merged.append(entry)
                    replaced = True
                    continue
                merged.append(
                    candidate.model_copy(
                        update={
                            "memory_id": entry.memory_id,
                            "created_at": entry.created_at,
                            "updated_at": datetime.now(UTC),
                            "tags": merged_tags,
                            "metadata": {**entry.metadata, **candidate.metadata},
                        }
                    )
                )
                replaced = True
            else:
                merged.append(entry)
        if not replaced:
            merged.append(candidate)
        merged.sort(key=lambda item: (item.importance, item.updated_at or item.created_at), reverse=True)
        return merged[:500]

    def _state(
        self,
        *,
        entries: list[AutobiographicalMemoryEntry],
        recent: list[AutobiographicalMemoryEntry],
        saved_entry: AutobiographicalMemoryEntry | None = None,
    ) -> AutobiographicalMemoryState:
        counts = Counter(entry.kind.value for entry in entries)
        important = [entry for entry in entries if entry.importance >= 80]
        summary = (
            "Memoria autobiografica activa: CEIBO puede recuperar objetivos, decisiones, "
            "preferencias y estado del proyecto antes de responder."
            if entries
            else "Memoria autobiografica vacia: falta sembrar objetivos, preferencias y decisiones."
        )
        warnings: list[str] = []
        if counts.get("goal", 0) == 0:
            warnings.append("Falta al menos un objetivo principal persistido.")
        if counts.get("preference", 0) == 0:
            warnings.append("Faltan preferencias del usuario para adaptar respuestas.")
        if counts.get("decision", 0) == 0:
            warnings.append("Faltan decisiones tecnicas persistidas.")
        if counts.get("project_state", 0) == 0:
            warnings.append("Falta estado del proyecto para continuidad entre sesiones.")

        next_actions = [
            "Registrar decisiones al cerrar cada sprint.",
            "Guardar preferencias del usuario cuando corrija el estilo de trabajo.",
            "Actualizar project_state despues de commits importantes.",
        ]
        return AutobiographicalMemoryState(
            status="autobiographical_memory_active" if entries else "autobiographical_memory_empty",
            summary=summary,
            memory_path=str(self.memory_path()),
            total_entries=len(entries),
            kind_counts=dict(counts),
            important_entries=important[:6],
            recent_entries=recent,
            saved_entry=saved_entry,
            warnings=warnings,
            next_actions=next_actions,
        )

    def _context_line(self, entry: AutobiographicalMemoryEntry) -> str:
        return f"{entry.kind}: {entry.title} - {entry.content}"

    def _stable_id(self, kind: str, title: str, content: str) -> str:
        seed = f"{kind}:{title.lower()}:{content[:80].lower()}"
        return f"auto-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"

    def _terms(self, text: str) -> set[str]:
        return {part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(part) > 3}

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in tags:
            clean = str(tag).strip().lower().replace(" ", "-")[:48]
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized[:16]


autobiographical_memory_service = AutobiographicalMemoryService()
