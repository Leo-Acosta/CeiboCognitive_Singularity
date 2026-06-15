from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from ceibo_core.core.config import settings
from ceibo_core.services.weather import weather_service


@dataclass(frozen=True)
class ChatToolResult:
    tool_name: str
    status: str
    answer: str
    focus: str
    next_steps: list[str] = field(default_factory=list)
    audit_notes: list[str] = field(default_factory=list)


class ChatToolRouter:
    """Read-only tool router for practical chat questions.

    This layer keeps tool use deterministic and auditable. It does not execute
    state-changing actions; commands are limited to short read-only probes.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or self._default_repo_root()

    async def route(self, message: str, context: list[str] | None = None) -> ChatToolResult | None:
        normalized = message.lower()
        if self._is_weather(normalized):
            return await self._weather(message)
        if self._is_datetime(normalized):
            return self._datetime()
        if self._is_git_status(normalized):
            return self._git_status()
        if self._is_docker_status(normalized):
            return self._docker_status()
        if self._is_project_status(normalized):
            return self._project_status(context or [])
        return None

    def _is_weather(self, message: str) -> bool:
        return any(keyword in message for keyword in ("clima", "temperatura", "pronostico")) or (
            "tiempo" in message and not any(keyword in message for keyword in ("hora", "fecha"))
        )

    def _is_datetime(self, message: str) -> bool:
        return any(
            keyword in message
            for keyword in (
                "que hora",
                "hora es",
                "fecha",
                "que dia",
                "dia es",
                "hoy",
            )
        )

    def _is_git_status(self, message: str) -> bool:
        return any(keyword in message for keyword in ("git", "commit", "rama", "branch", "cambios pendientes"))

    def _is_docker_status(self, message: str) -> bool:
        return any(keyword in message for keyword in ("docker", "contenedor", "contenedores", "servicios"))

    def _is_project_status(self, message: str) -> bool:
        return any(
            phrase in message
            for phrase in (
                "que hace este proyecto",
                "estado del proyecto",
                "estado de ceibo",
                "capacidades tiene",
                "que modulos tiene",
                "que sprint",
                "en que estamos",
            )
        )

    async def _weather(self, message: str) -> ChatToolResult:
        observation = await weather_service.current_weather(message)
        if observation.status == "ok":
            location = ", ".join(
                part for part in [observation.location, observation.country] if part
            )
            answer = (
                f"Ahora en {location} hay {observation.temperature_c}°C "
                f"(sensacion {observation.apparent_temperature_c}°C), "
                f"{observation.condition}. Humedad {observation.humidity_percent}% "
                f"y viento {observation.wind_kmh} km/h."
            )
            return ChatToolResult(
                tool_name="weather.current",
                status="ok",
                answer=answer,
                focus="consulta de clima",
                next_steps=[
                    f"Fuente: {observation.provider} / Open-Meteo.",
                    f"Hora de observacion: {observation.observed_at}.",
                    "Para otra ciudad, pregunta por ejemplo: clima en Madrid.",
                ],
                audit_notes=["tool=weather.current", "mode=read_only_external"],
            )
        if observation.status == "not_found":
            answer = f"No pude encontrar la ubicacion `{observation.location}` para consultar el clima."
            next_steps = [
                "Probar con ciudad y pais, por ejemplo: tiempo en Cordoba, Argentina.",
                "Evitar nombres ambiguos o incompletos.",
            ]
        elif observation.status == "missing_location":
            answer = "Puedo consultar el clima, pero necesito una ciudad o ubicacion."
            next_steps = [
                "Ejemplo: dime el tiempo en Buenos Aires.",
                "Ejemplo: clima en Madrid.",
            ]
        else:
            answer = "La herramienta de clima esta integrada, pero ahora no pude consultar el proveedor externo."
            next_steps = [observation.error or "Reintentar la consulta en unos segundos."]
        return ChatToolResult(
            tool_name="weather.current",
            status=observation.status,
            answer=answer,
            focus="consulta de clima",
            next_steps=next_steps,
            audit_notes=["tool=weather.current", "mode=read_only_external"],
        )

    def _datetime(self) -> ChatToolResult:
        local_tz = timezone(timedelta(hours=-3), name="America/Buenos_Aires")
        now = datetime.now(UTC).astimezone(local_tz)
        return ChatToolResult(
            tool_name="time.local",
            status="ok",
            answer=(
                "La hora local configurada para CEIBO es "
                f"{now.strftime('%H:%M')} del {now.strftime('%Y-%m-%d')} "
                "(America/Buenos_Aires)."
            ),
            focus="hora y fecha",
            next_steps=[
                "Si necesitas otra zona horaria, indicame ciudad o pais.",
                "Puedo usar esta hora como referencia para auditoria o planificacion.",
            ],
            audit_notes=["tool=time.local", "mode=read_only_local"],
        )

    def _git_status(self) -> ChatToolResult:
        branch = self._run_read_only(["git", "branch", "--show-current"])
        latest = self._run_read_only(["git", "log", "-1", "--pretty=%h %s"])
        status = self._run_read_only(["git", "status", "--short"])
        if branch.status != "ok":
            return ChatToolResult(
                tool_name="git.status",
                status="unavailable",
                answer="No pude leer Git desde este runtime.",
                focus="estado de git",
                next_steps=[
                    branch.output or "Verificar que el runtime tenga acceso al repo y a .git.",
                ],
                audit_notes=["tool=git.status", "mode=read_only_local"],
            )
        pending = status.output.strip() or "sin cambios pendientes"
        return ChatToolResult(
            tool_name="git.status",
            status="ok",
            answer=(
                f"Git esta en la rama `{branch.output.strip()}`. "
                f"Ultimo commit: {latest.output.strip() or 'no disponible'}. "
                f"Estado: {pending}."
            ),
            focus="estado de git",
            next_steps=[
                "Si queres, puedo preparar un resumen de cambios antes del proximo commit.",
                "No hago commit ni push desde el chat sin confirmacion explicita.",
            ],
            audit_notes=["tool=git.status", "mode=read_only_local"],
        )

    def _docker_status(self) -> ChatToolResult:
        result = self._run_read_only(["docker", "compose", "ps", "--format", "table {{.Name}}\t{{.Service}}\t{{.State}}"])
        if result.status != "ok":
            return ChatToolResult(
                tool_name="docker.status",
                status="unavailable",
                answer="No pude leer Docker desde este runtime.",
                focus="estado de docker",
                next_steps=[
                    result.output or "Verificar que Docker este disponible para el proceso del API.",
                    "Tambien podes revisar Docker Desktop manualmente.",
                ],
                audit_notes=["tool=docker.status", "mode=read_only_local"],
            )
        return ChatToolResult(
            tool_name="docker.status",
            status="ok",
            answer=f"Estado Docker Compose:\n{result.output.strip()}",
            focus="estado de docker",
            next_steps=[
                "Esto es solo lectura; iniciar, detener o borrar contenedores requiere confirmacion.",
                "Si un servicio aparece caido, puedo proponer diagnostico antes de ejecutar acciones.",
            ],
            audit_notes=["tool=docker.status", "mode=read_only_local"],
        )

    def _project_status(self, context: list[str]) -> ChatToolResult:
        memory_hint = next((item for item in context if "nucleo cognitivo" in item.lower()), "")
        answer = (
            "CEIBO CORE es un nucleo cognitivo local para interpretar pedidos, recordar decisiones, "
            "usar herramientas controladas, generar datasets, evaluar respuestas y preparar entrenamiento. "
            "Hoy ya funciona como sistema local con API, frontend, memoria, DevCore, safety gates, "
            "dataset expansion, evaluation loop, voz autorizada inicial y herramientas de chat."
        )
        if memory_hint:
            answer += " Mantiene como objetivo central servir de logica y discernimiento para un futuro robot."
        return ChatToolResult(
            tool_name="project.status",
            status="ok",
            answer=answer,
            focus="estado del proyecto",
            next_steps=[
                "Seguir ampliando herramientas del chat con respuestas reales.",
                "Conectar Project Knowledge Answers para responder sobre modulos, sprints y capacidades.",
                "Mantener gates de seguridad antes de ejecucion real.",
            ],
            audit_notes=["tool=project.status", "mode=read_only_local"],
        )

    def _run_read_only(self, command: list[str]) -> "_CommandResult":
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _CommandResult(status="unavailable", output=str(exc))
        output = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode != 0:
            return _CommandResult(status="unavailable", output=output)
        return _CommandResult(status="ok", output=output)

    def _default_repo_root(self) -> Path:
        return Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class _CommandResult:
    status: str
    output: str


chat_tool_router = ChatToolRouter()
