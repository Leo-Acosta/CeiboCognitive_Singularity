import json
import re
from typing import Any

import httpx

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    TeacherReviewRequest,
    TeacherReviewResponse,
    TeacherStatus,
    TeacherSyntheticRequest,
    TeacherSyntheticResponse,
    TrainingExample,
    TrainingFeedbackRating,
)


JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
JSON_STRING_PATTERN = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')


class TeacherAgentService:
    async def status(self) -> TeacherStatus:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{settings.teacher_base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
            models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
            return TeacherStatus(
                provider=settings.teacher_provider,
                base_url=settings.teacher_base_url,
                model=settings.teacher_model,
                available=settings.teacher_model in models,
                installed_models=models,
            )
        except httpx.HTTPError as exc:
            return TeacherStatus(
                provider=settings.teacher_provider,
                base_url=settings.teacher_base_url,
                model=settings.teacher_model,
                available=False,
                error=str(exc),
            )

    async def review_response(self, request: TeacherReviewRequest) -> TeacherReviewResponse:
        prompt = self._review_prompt(request)
        raw_feedback = await self._ollama_generate(prompt)
        parsed = self._parse_json_object(raw_feedback)
        score = self._clamp_score(parsed.get("score", 0))
        issues = self._string_list(parsed.get("issues", []))
        strengths = self._string_list(parsed.get("strengths", []))
        ideal_response = str(parsed.get("ideal_response") or "").strip()

        if not ideal_response:
            ideal_response = request.ceibo_response
            issues.append("Teacher IA no devolvio respuesta ideal estructurada.")

        return TeacherReviewResponse(
            prompt=request.prompt,
            ceibo_response=request.ceibo_response,
            teacher_model=settings.teacher_model,
            score=score,
            passed=score >= 75,
            issues=issues,
            strengths=strengths,
            ideal_response=ideal_response,
            raw_feedback=raw_feedback,
        )

    async def generate_synthetic_examples(
        self,
        request: TeacherSyntheticRequest,
    ) -> TeacherSyntheticResponse:
        prompt = self._synthetic_prompt(request)
        raw_output = await self._ollama_generate(prompt)
        parsed = self._parse_json_object(raw_output)
        examples_payload = parsed.get("examples", [])
        examples: list[TrainingExample] = []

        for payload in examples_payload if isinstance(examples_payload, list) else []:
            if not isinstance(payload, dict):
                continue
            instruction = str(payload.get("instruction") or "").strip()
            response = str(payload.get("response") or "").strip()
            if not instruction or not response:
                continue
            tags = self._string_list(payload.get("tags", []))
            examples.append(
                TrainingExample(
                    instruction=instruction,
                    input=str(payload.get("input") or "").strip(),
                    response=response,
                    tags=list(dict.fromkeys([*request.tags, *tags, "teacher:mistral"])),
                    source="ollama-mistral-teacher",
                    rating=TrainingFeedbackRating.GOOD,
                    metadata={
                        "teacher_model": settings.teacher_model,
                        "topic": request.topic,
                        "difficulty": request.difficulty,
                    },
                )
            )

        return TeacherSyntheticResponse(
            teacher_model=settings.teacher_model,
            examples=examples[: request.count],
            raw_output=raw_output,
        )

    async def _ollama_generate(self, prompt: str) -> str:
        payload = {
            "model": settings.teacher_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
            },
        }
        async with httpx.AsyncClient(timeout=settings.teacher_timeout_seconds) as client:
            response = await client.post(f"{settings.teacher_base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return str(data.get("response", "")).strip()

    def _review_prompt(self, request: TeacherReviewRequest) -> str:
        traits = "\n".join(f"- {trait}" for trait in request.expected_traits) or "- claridad\n- utilidad\n- pasos accionables"
        return f"""
Eres Teacher IA local para CEIBO CORE. Tu trabajo es ensenar, corregir y mejorar
respuestas para entrenar un asistente local tipo Jarvis.

Directiva maestra de CEIBO:
Ayudar y ensenar a su usuario principal con respuestas claras, utiles,
accionables y adaptadas a lo que necesite.

Categoria: {request.category}

Prompt del usuario:
{request.prompt}

Respuesta actual de CEIBO:
{request.ceibo_response}

Rasgos esperados:
{traits}

Devuelve SOLO JSON valido con esta forma:
{{
  "score": 0,
  "passed": false,
  "issues": ["problema concreto"],
  "strengths": ["fortaleza concreta"],
  "ideal_response": "respuesta ideal en espanol, clara, educativa y accionable"
}}

Reglas obligatorias:
- Todo el contenido de texto debe estar en espanol.
- "score" debe ser un entero de 0 a 100, nunca decimal.
- No uses markdown fuera del JSON.
""".strip()

    def _synthetic_prompt(self, request: TeacherSyntheticRequest) -> str:
        tags = ", ".join(request.tags) if request.tags else "ceibo, training"
        return f"""
Eres Teacher IA local para CEIBO CORE. Genera datos de entrenamiento de alta
calidad para fine-tuning. Cada ejemplo debe ensenar a CEIBO a ayudar y explicar
mejor a su usuario principal.

Tema: {request.topic}
Dificultad: {request.difficulty}
Cantidad: {request.count}
Tags base: {tags}

Devuelve SOLO JSON valido con esta forma:
{{
  "examples": [
    {{
      "instruction": "pregunta u orden del usuario",
      "input": "contexto opcional",
      "response": "respuesta ideal de CEIBO, clara, util y accionable",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}
""".strip()

    def _parse_json_object(self, value: str) -> dict[str, Any]:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            match = JSON_OBJECT_PATTERN.search(value)
            if not match:
                return {}
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return self._parse_jsonish_object(match.group(0))

    def _parse_jsonish_object(self, value: str) -> dict[str, Any]:
        score_match = re.search(r'"score"\s*:\s*([0-9]+(?:\.[0-9]+)?)', value)
        passed_match = re.search(r'"passed"\s*:\s*(true|false)', value, re.IGNORECASE)
        ideal_response_match = re.search(
            r'"ideal_response"\s*:\s*"(.*?)"\s*(?:,?\s*})',
            value,
            re.DOTALL,
        )
        parsed: dict[str, Any] = {
            "issues": self._parse_jsonish_list(value, "issues"),
            "strengths": self._parse_jsonish_list(value, "strengths"),
        }
        if score_match:
            parsed["score"] = score_match.group(1)
        if passed_match:
            parsed["passed"] = passed_match.group(1).lower() == "true"
        if ideal_response_match:
            parsed["ideal_response"] = self._decode_jsonish_string(
                ideal_response_match.group(1)
            )
        return parsed

    def _parse_jsonish_list(self, value: str, key: str) -> list[str]:
        list_match = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', value, re.DOTALL)
        if not list_match:
            return []
        return [
            self._decode_jsonish_string(item)
            for item in JSON_STRING_PATTERN.findall(list_match.group(1))
        ]

    def _decode_jsonish_string(self, value: str) -> str:
        try:
            decoded = json.loads(f'"{value}"')
        except json.JSONDecodeError:
            decoded = value.replace("\\n", "\n")
        return str(decoded).strip()

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _clamp_score(self, value: Any) -> int:
        try:
            score_value = float(value)
        except (TypeError, ValueError):
            score_value = 0
        if 0 < score_value <= 1:
            score_value *= 100
        return max(0, min(round(score_value), 100))


teacher_agent_service = TeacherAgentService()
