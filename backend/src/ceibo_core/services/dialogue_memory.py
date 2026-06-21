from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ceibo_core.core.config import settings


class DialogueMemoryService:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or "./data/dialogue_memory.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> List[dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []

    def _write(self, data: List[dict]) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    async def remember(self, kind: str, title: str, content: str, importance: int = 50, tags: List[str] | None = None) -> None:
        tags = tags or []
        records = self._read()
        records.append({"kind": kind, "title": title, "content": content, "importance": importance, "tags": tags})
        self._write(records)

    async def get_relevant_memory_context(self, user_message: str) -> str:
        records = self._read()
        # simple relevance: include records with any keyword present
        words = set(user_message.lower().split())
        matched = []
        for r in records:
            content_words = set(r.get("content", "").lower().split())
            if words & content_words:
                matched.append(r.get("content"))
        return "\n".join(matched[:5])


dialogue_memory_service = DialogueMemoryService()
