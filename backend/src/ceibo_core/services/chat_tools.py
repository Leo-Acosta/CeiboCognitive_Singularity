from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from ceibo_core.core.config import settings
from ceibo_core.services.entertainment import entertainment_service
from ceibo_core.services.external_market import external_market_service
from ceibo_core.services.project_knowledge import project_knowledge_service
from ceibo_core.services.travel_booking import travel_booking_service
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
        normalized = project_knowledge_service.normalize(message)
        if self._is_weather(normalized):
            return await self._weather(message)
        if self._is_currency(normalized):
            return await self._currency(message)
        if self._is_stock(normalized):
            return await self._stock(message)
        if self._is_country_condition(normalized):
            return await self._country_condition(message)
        if self._is_travel(normalized):
            return self._travel(message, context or [])
        if self._is_entertainment(normalized):
            return self._entertainment(message, context or [])
        if self._is_datetime(normalized):
            return self._datetime()
        if self._is_git_status(normalized):
            return self._git_status()
        if self._is_docker_status(normalized):
            return self._docker_status()
        if self._is_project_status(normalized):
            return self._project_status(message, context or [])
        return None

    def _is_weather(self, message: str) -> bool:
        return any(
            keyword in message
            for keyword in (
                "clima",
                "temperatura",
                "pronostico",
                "llover",
                "llueve",
                "lluvia",
                "tormenta",
                "estado del tiempo",
            )
        ) or (
            "tiempo" in message and not any(keyword in message for keyword in ("hora", "fecha"))
        )

    def _is_weather_forecast(self, message: str) -> bool:
        normalized = project_knowledge_service.normalize(message)
        return any(
            keyword in normalized
            for keyword in (
                "pronostico",
                "llover",
                "llueve",
                "lluvia",
                "proximos dias",
                "manana",
                "semana",
                "forecast",
            )
        )

    def _is_currency(self, message: str) -> bool:
        return any(
            keyword in message
            for keyword in (
                "dolar",
                "dolares",
                "usd",
                "euro",
                "eur",
                "tipo de cambio",
                "cotizacion del dolar",
                "valor del dolar",
                "calor del dolar",
            )
        )

    def _is_stock(self, message: str) -> bool:
        return any(
            keyword in message
            for keyword in (
                "accion",
                "acciones",
                "stock",
                "ticker",
                "cotiza",
                "cotizan",
                "nasdaq",
                "nyse",
            )
        )

    def _is_country_condition(self, message: str) -> bool:
        return any(
            phrase in message
            for phrase in (
                "condicion de la nacion",
                "estado de la nacion",
                "situacion del pais",
                "situacion de la nacion",
                "como esta la nacion",
                "como esta el pais",
                "panorama del pais",
                "panorama de argentina",
            )
        )

    def _is_entertainment(self, message: str) -> bool:
        return any(
            keyword in message
            for keyword in (
                "cartelera",
                "cine",
                "teatro",
                "obra",
                "obras",
                "pelicula",
                "peliculas",
                "espectaculo",
                "espectaculos",
                "show",
                "shows",
                "recital",
                "concierto",
                "conciertos",
                "entradas",
                "ticket",
                "tickets",
                "comprar entrada",
                "comprar ticket",
            )
        )

    def _is_travel(self, message: str) -> bool:
        if any(keyword in message for keyword in ("cartelera", "teatro", "cine", "show", "recital")):
            return False
        travel_phrases = ("ida y vuelta", "comprar pasaje", "comprar pasajes", "medio de transporte")
        if any(phrase in message for phrase in travel_phrases):
            return True
        tokens = set(message.replace("/", " ").replace("-", " ").split())
        travel_tokens = {
            "pasaje",
            "pasajes",
            "vuelo",
            "vuelos",
            "avion",
            "aereo",
            "micro",
            "omnibus",
            "autobus",
            "bus",
            "tren",
            "ferry",
            "barco",
            "transporte",
            "viajar",
            "viaje",
        }
        return bool(tokens & travel_tokens)

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
        return project_knowledge_service.should_answer(message)

    async def _weather(self, message: str) -> ChatToolResult:
        if self._is_weather_forecast(message):
            return await self._weather_forecast(message)
        observation = await weather_service.current_weather(message)
        if observation.status == "ok":
            location = ", ".join(
                part for part in [observation.location, observation.country] if part
            )
            temperature = f"{observation.temperature_c} C"
            apparent = f"{observation.apparent_temperature_c} C"
            answer = (
                f"Ahora en {location} hay {temperature} "
                f"(sensacion {apparent}), "
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

    async def _weather_forecast(self, message: str) -> ChatToolResult:
        forecast = await weather_service.daily_forecast(message)
        if forecast.status == "ok":
            location = ", ".join(part for part in [forecast.location, forecast.country] if part)
            rainy_days = [
                day
                for day in forecast.days
                if (day.precipitation_probability_max or 0) >= 40 or (day.precipitation_mm or 0) > 0
            ]
            if rainy_days:
                rain_summary = "Hay chance de lluvia en " + ", ".join(
                    f"{day.date} ({day.precipitation_probability_max or 0}%, {day.precipitation_mm or 0} mm)"
                    for day in rainy_days[:3]
                )
            else:
                rain_summary = "No aparecen senales fuertes de lluvia en los proximos dias."
            daily_lines = [
                (
                    f"- {day.date}: {day.condition}, "
                    f"{day.temperature_min_c} a {day.temperature_max_c} C, "
                    f"lluvia {day.precipitation_probability_max or 0}%."
                )
                for day in forecast.days[:5]
            ]
            return ChatToolResult(
                tool_name="weather.forecast",
                status="ok",
                answer=f"Pronostico para {location}: {rain_summary}\n" + "\n".join(daily_lines),
                focus="pronostico de clima",
                next_steps=[
                    f"Fuente: {forecast.provider} / Open-Meteo.",
                    "El pronostico puede cambiar; conviene revisarlo cerca del horario de salida.",
                    "Para otra ciudad, pregunta por ejemplo: llovera en Montevideo?",
                ],
                audit_notes=["tool=weather.forecast", "mode=read_only_external"],
            )
        if forecast.status == "not_found":
            answer = f"No pude encontrar la ubicacion `{forecast.location}` para consultar el pronostico."
            next_steps = ["Probar con ciudad y pais, por ejemplo: pronostico en Cordoba, Argentina."]
        elif forecast.status == "missing_location":
            answer = "Puedo consultar pronostico, pero necesito una ciudad o ubicacion."
            next_steps = ["Ejemplo: llovera en Buenos Aires los proximos dias?"]
        else:
            answer = "La herramienta de pronostico esta integrada, pero ahora no pude consultar el proveedor externo."
            next_steps = [forecast.error or "Reintentar la consulta en unos segundos."]
        return ChatToolResult(
            tool_name="weather.forecast",
            status=forecast.status,
            answer=answer,
            focus="pronostico de clima",
            next_steps=next_steps,
            audit_notes=["tool=weather.forecast", "mode=read_only_external"],
        )

    async def _currency(self, message: str) -> ChatToolResult:
        quote = await external_market_service.currency(message)
        if quote.status == "ok":
            return ChatToolResult(
                tool_name="market.currency",
                status="ok",
                answer=f"{quote.base}/{quote.target}: 1 {quote.base} = {quote.rate} {quote.target}.",
                focus="cotizacion de moneda",
                next_steps=[
                    f"Fuente: {quote.provider}.",
                    f"Fecha/hora de referencia: {quote.observed_at}.",
                    "Es cotizacion informativa; no es asesoramiento financiero.",
                ],
                audit_notes=["tool=market.currency", "mode=read_only_external"],
            )
        return ChatToolResult(
            tool_name="market.currency",
            status=quote.status,
            answer="No pude obtener la cotizacion solicitada.",
            focus="cotizacion de moneda",
            next_steps=[quote.error or "Probar con un par tipo USD/ARS o EUR/USD."],
            audit_notes=["tool=market.currency", "mode=read_only_external"],
        )

    async def _stock(self, message: str) -> ChatToolResult:
        quote = await external_market_service.stock(message)
        if quote.status == "ok":
            change = ""
            if quote.change is not None and quote.change_percent is not None:
                change = f" Cambio vs cierre previo: {quote.change} ({quote.change_percent}%)."
            return ChatToolResult(
                tool_name="market.stock",
                status="ok",
                answer=f"{quote.symbol}: {quote.price} {quote.currency}.{change}",
                focus="cotizacion de accion",
                next_steps=[
                    f"Fuente: {quote.provider}.",
                    f"Referencia: {quote.source_url}.",
                    "Es informacion de mercado con posible demora; no es recomendacion de inversion.",
                ],
                audit_notes=["tool=market.stock", "mode=read_only_external"],
            )
        if quote.status == "missing_symbol":
            answer = "Puedo consultar acciones, pero necesito el simbolo/ticker."
            next_steps = ["Ejemplo: como cotiza AAPL?", "Ejemplo: cotizacion de GGAL.BA."]
        else:
            answer = f"No pude obtener la cotizacion de `{quote.symbol}`."
            next_steps = [quote.error or "Verificar el ticker."]
        return ChatToolResult(
            tool_name="market.stock",
            status=quote.status,
            answer=answer,
            focus="cotizacion de accion",
            next_steps=next_steps,
            audit_notes=["tool=market.stock", "mode=read_only_external"],
        )

    async def _country_condition(self, message: str) -> ChatToolResult:
        condition = await external_market_service.country_condition(message)
        if condition.status in {"ok", "partial"}:
            indicators = "\n".join(f"- {indicator}" for indicator in condition.indicators) or "- Sin indicadores disponibles."
            provider_note = [f"Advertencia: {condition.error}."] if condition.error else []
            return ChatToolResult(
                tool_name="country.condition",
                status=condition.status,
                answer=f"{condition.summary}\n{indicators}",
                focus="panorama pais",
                next_steps=[
                    *provider_note,
                    "Para noticias en tiempo real hace falta integrar un proveedor de noticias.",
                    "Para decision economica o politica, contrastar con fuentes oficiales y medios confiables.",
                    *[f"Fuente: {source}" for source in condition.source_urls],
                ],
                audit_notes=["tool=country.condition", "mode=read_only_external"],
            )
        return ChatToolResult(
            tool_name="country.condition",
            status=condition.status,
            answer=condition.summary,
            focus="panorama pais",
            next_steps=[condition.error or "Reintentar o indicar pais concreto."],
            audit_notes=["tool=country.condition", "mode=read_only_external"],
        )

    def _entertainment(self, message: str, context: list[str]) -> ChatToolResult:
        search = entertainment_service.search(message, context)
        if search.status == "needs_preference":
            return ChatToolResult(
                tool_name="entertainment.discovery",
                status="needs_preference",
                answer=search.next_question or "Que queres ver?",
                focus="cartelera y tickets",
                next_steps=[
                    f"Ciudad base: {search.city or 'CABA'}.",
                    "Ejemplos: teatro en CABA, cine en Madrid, recitales en New York, entradas para Fuerza Bruta.",
                    *search.source_notes,
                ],
                audit_notes=["tool=entertainment.discovery", "mode=read_only_external_handoff"],
            )
        option_lines = [
            (
                f"- {option.source}: {option.title}\n"
                f"  Comprar/reservar: {option.ticket_url}\n"
                f"  Nota: {option.note}"
            )
            for option in search.options[:5]
        ]
        return ChatToolResult(
            tool_name="entertainment.discovery",
            status="ok",
            answer=(
                f"Para {search.category} en {search.city}, buscaria `{search.query}` en estas carteleras:\n"
                + "\n".join(option_lines)
            ),
            focus="cartelera y tickets",
            next_steps=[
                "Decime fecha, presupuesto o zona y filtro mejor.",
                "Cuando elijas una opcion, te puedo guiar hasta el paso previo al pago.",
                *search.source_notes,
            ],
            audit_notes=["tool=entertainment.discovery", "mode=read_only_external_handoff"],
        )

    def _travel(self, message: str, context: list[str]) -> ChatToolResult:
        search = travel_booking_service.search(message, context)
        if search.status == "needs_details":
            return ChatToolResult(
                tool_name="travel.tickets",
                status="needs_details",
                answer=search.next_question or "Que pasaje queres buscar?",
                focus="pasajes y transporte",
                next_steps=[
                    f"Datos faltantes: {', '.join(search.missing_fields)}.",
                    "Puedo orientar avion, micro, tren, ferry o ruta multimodal.",
                    *search.source_notes,
                ],
                audit_notes=["tool=travel.tickets", "mode=read_only_external_handoff"],
            )
        option_lines = [
            (
                f"- {option.source}: {option.mode} {search.origin} -> {search.destination}\n"
                f"  Comprar/buscar: {option.booking_url}\n"
                f"  Nota: {option.note}"
            )
            for option in search.options[:5]
        ]
        return ChatToolResult(
            tool_name="travel.tickets",
            status="ok",
            answer=(
                f"Para {search.passengers} pasajero(s), {travel_booking_service.mode_labels.get(search.mode or '', search.mode)} de {search.origin} "
                f"a {search.destination} el {search.departure_date}, prepararia estas opciones:\n"
                + "\n".join(option_lines)
            ),
            focus="pasajes y transporte",
            next_steps=[
                "Antes de pagar revisa equipaje, terminal/aeropuerto, escalas, horario y condiciones de cambio.",
                "CEIBO todavia no compra ni guarda medio de pago; te guia hasta la plataforma externa.",
                *search.source_notes,
            ],
            audit_notes=["tool=travel.tickets", "mode=read_only_external_handoff"],
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

    def _project_status(self, message: str, context: list[str]) -> ChatToolResult:
        answer = project_knowledge_service.answer(message, context)
        return ChatToolResult(
            tool_name=f"project.knowledge.{answer.topic}",
            status="ok",
            answer=answer.answer,
            focus="conocimiento del proyecto",
            next_steps=[*answer.evidence, *answer.next_steps],
            audit_notes=[f"tool=project.knowledge", f"topic={answer.topic}", "mode=read_only_local"],
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
