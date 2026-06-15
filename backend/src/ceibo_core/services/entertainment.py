from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from ceibo_core.services.project_knowledge import project_knowledge_service


@dataclass(frozen=True)
class EntertainmentOption:
    title: str
    category: str
    city: str
    source: str
    search_url: str
    ticket_url: str
    note: str


@dataclass(frozen=True)
class EntertainmentSearch:
    status: str
    prompt: str
    city: str | None = None
    category: str | None = None
    query: str | None = None
    options: list[EntertainmentOption] = field(default_factory=list)
    next_question: str | None = None
    source_notes: list[str] = field(default_factory=list)


class EntertainmentService:
    """Cartelera assistant with safe purchase handoff links.

    This does not buy tickets or handle payments. It guides the user to trusted
    listing/ticket providers and keeps the final purchase outside CEIBO until a
    payment provider is explicitly configured.
    """

    default_city = "CABA"
    category_aliases = {
        "cine": ("cine", "pelicula", "peliculas", "movie", "movies", "cartelera de cine"),
        "teatro": ("teatro", "obra", "obras", "musical", "stand up", "standup"),
        "conciertos": ("concierto", "conciertos", "recital", "musica", "show", "festival"),
        "familia": ("familia", "infantil", "ninos", "niños", "kids"),
    }
    city_aliases = {
        "caba": "CABA",
        "buenos aires": "CABA",
        "capital federal": "CABA",
        "argentina": "CABA",
        "cordoba": "Cordoba",
        "córdoba": "Cordoba",
        "rosario": "Rosario",
        "mendoza": "Mendoza",
        "montevideo": "Montevideo",
        "madrid": "Madrid",
        "barcelona": "Barcelona",
        "new york": "New York",
        "nueva york": "New York",
        "londres": "London",
        "london": "London",
        "paris": "Paris",
        "ciudad de mexico": "Ciudad de Mexico",
        "méxico": "Ciudad de Mexico",
        "mexico": "Ciudad de Mexico",
        "santiago": "Santiago",
        "sao paulo": "Sao Paulo",
        "rio de janeiro": "Rio de Janeiro",
    }

    def search(self, message: str, context: list[str] | None = None) -> EntertainmentSearch:
        normalized = project_knowledge_service.normalize(message)
        city = self.extract_city(normalized, context or [])
        category = self.extract_category(normalized)
        query = self.extract_query(message, normalized)

        if (not category and not query) or (category == "espectaculos" and not query):
            return EntertainmentSearch(
                status="needs_preference",
                prompt=message,
                city=city or self.default_city,
                next_question=(
                    "Que queres ver? Podes decir cine, teatro, recitales, stand up, algo familiar "
                    "o el nombre de una obra/pelicula/artista."
                ),
                source_notes=[
                    "Todavia no compro tickets ni procesa pagos.",
                    "Cuando elijas, preparo enlaces de compra/reserva en plataformas externas.",
                ],
            )

        safe_city = city or self.default_city
        safe_category = category or "espectaculos"
        safe_query = query or safe_category
        return EntertainmentSearch(
            status="ok",
            prompt=message,
            city=safe_city,
            category=safe_category,
            query=safe_query,
            options=self._options(city=safe_city, category=safe_category, query=safe_query),
            source_notes=[
                "Compra final fuera de CEIBO hasta configurar medio de pago.",
                "Verificar fecha, ubicacion, butacas, cargos y politica de reembolso en la plataforma elegida.",
            ],
        )

    def extract_city(self, normalized_message: str, context: list[str]) -> str | None:
        for alias, city in self.city_aliases.items():
            if alias in normalized_message:
                return city
        match = re.search(r"\b(?:en|para)\s+([a-zA-Z\s.'-]{3,40})$", normalized_message)
        if match:
            candidate = match.group(1).strip(" ?.!,")
            if candidate not in {"cartelera", "cine", "teatro", "show", "shows"}:
                return candidate.title()
        for item in reversed(context):
            normalized_context = project_knowledge_service.normalize(item)
            for alias, city in self.city_aliases.items():
                if alias in normalized_context:
                    return city
        return None

    def extract_category(self, normalized_message: str) -> str | None:
        for category, aliases in self.category_aliases.items():
            if any(alias in normalized_message for alias in aliases):
                return category
        if any(term in normalized_message for term in ("cartelera", "entrada", "entradas", "ticket", "tickets", "espectaculo")):
            return "espectaculos"
        return None

    def extract_query(self, message: str, normalized_message: str) -> str | None:
        patterns = [
            r"\b(?:quiero ver|me gustaria ver|busca|buscar|ver)\s+(.+)$",
            r"\b(?:entradas para|tickets para|cartelera de)\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                query = match.group(1).strip(" ?.!,")
                if query and project_knowledge_service.normalize(query) not in {"cine", "teatro", "cartelera", "espectaculos"}:
                    return query
        if any(term in normalized_message for term in ("cartelera", "entrada", "entradas", "ticket", "tickets")):
            return None
        return None

    def _options(self, city: str, category: str, query: str) -> list[EntertainmentOption]:
        providers = self._providers_for(city, category)
        return [
            EntertainmentOption(
                title=f"{category.title()} en {city}: {query}",
                category=category,
                city=city,
                source=provider["source"],
                search_url=provider["search_url"](query, city),
                ticket_url=provider["ticket_url"](query, city),
                note=provider["note"],
            )
            for provider in providers
        ]

    def _providers_for(self, city: str, category: str) -> list[dict[str, object]]:
        if city == "CABA" and category == "cine":
            return [
                self._provider("Cinemark Hoyts", "https://www.cinemarkhoyts.com.ar/search?q={query}", "cartelera de cine y compra externa"),
                self._provider("Google Cartelera", "https://www.google.com/search?q={query}+cine+{city}+cartelera", "busqueda agregada"),
            ]
        if city == "CABA" and category in {"teatro", "espectaculos", "familia"}:
            return [
                self._provider("Alternativa Teatral", "https://www.alternativateatral.com/buscar.asp?texto={query}", "teatro independiente y reservas externas"),
                self._provider("Plateanet", "https://www.plateanet.com/buscar/{query}", "teatro, shows y compra externa"),
                self._provider("Ticketek Argentina", "https://www.ticketek.com.ar/search?q={query}", "eventos masivos y compra externa"),
            ]
        if city == "CABA" and category == "conciertos":
            return [
                self._provider("Ticketek Argentina", "https://www.ticketek.com.ar/search?q={query}", "recitales y compra externa"),
                self._provider("Passline", "https://www.passline.com/search?q={query}", "shows y eventos"),
            ]
        return [
            self._provider("Ticketmaster", "https://www.ticketmaster.com/search?q={query}+{city}", "eventos internacionales y compra externa"),
            self._provider("Eventbrite", "https://www.eventbrite.com/d/{city}/{query}/", "eventos independientes"),
            self._provider("Google Events", "https://www.google.com/search?q={query}+{city}+tickets+cartelera", "busqueda agregada"),
        ]

    def _provider(self, source: str, template: str, note: str) -> dict[str, object]:
        def build_url(query: str, city: str) -> str:
            return template.format(query=quote_plus(query), city=quote_plus(city))

        return {
            "source": source,
            "search_url": build_url,
            "ticket_url": build_url,
            "note": note,
        }


entertainment_service = EntertainmentService()
