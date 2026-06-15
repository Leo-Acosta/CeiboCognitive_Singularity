from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from ceibo_core.services.project_knowledge import project_knowledge_service


@dataclass(frozen=True)
class TravelTicketOption:
    mode: str
    source: str
    search_url: str
    booking_url: str
    note: str


@dataclass(frozen=True)
class TravelTicketSearch:
    status: str
    prompt: str
    mode: str | None = None
    origin: str | None = None
    destination: str | None = None
    departure_date: str | None = None
    passengers: int = 1
    missing_fields: list[str] = field(default_factory=list)
    next_question: str | None = None
    options: list[TravelTicketOption] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)


class TravelBookingService:
    """Transport ticket assistant with safe external purchase handoff.

    CEIBO prepares search and booking links but never purchases tickets, stores
    payment methods, or confirms reservations without future explicit gates.
    """

    mode_aliases = {
        "flight": ("avion", "avion", "vuelo", "vuelos", "aereo", "aerea", "plane", "flight"),
        "bus": ("micro", "bus", "omnibus", "colectivo", "autobus"),
        "train": ("tren", "train", "ferrocarril"),
        "ferry": ("ferry", "barco", "buque", "lancha"),
        "multimodal": ("transporte", "pasaje", "pasajes", "ticket", "tickets", "viaje", "viajar"),
    }
    mode_labels = {
        "flight": "avion",
        "bus": "micro",
        "train": "tren",
        "ferry": "ferry",
        "multimodal": "transporte multimodal",
    }

    def search(self, message: str, context: list[str] | None = None) -> TravelTicketSearch:
        normalized = project_knowledge_service.normalize(message)
        mode = self.extract_mode(normalized)
        origin, destination = self.extract_route(message, normalized)
        departure_date = self.extract_date(message)
        passengers = self.extract_passengers(normalized)
        missing = []
        if not origin:
            missing.append("origen")
        if not destination:
            missing.append("destino")
        if not departure_date:
            missing.append("fecha")
        if not mode:
            missing.append("medio de transporte")

        if missing:
            return TravelTicketSearch(
                status="needs_details",
                prompt=message,
                mode=mode,
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                passengers=passengers,
                missing_fields=missing,
                next_question=self._question_for_missing(missing, mode, origin, destination, departure_date),
                source_notes=[
                    "No compro ni reservo pasajes todavia.",
                    "Cuando completes los datos preparo enlaces externos de compra.",
                ],
            )

        safe_mode = mode or "multimodal"
        safe_origin = origin or ""
        safe_destination = destination or ""
        safe_date = departure_date or ""
        return TravelTicketSearch(
            status="ok",
            prompt=message,
            mode=safe_mode,
            origin=safe_origin,
            destination=safe_destination,
            departure_date=safe_date,
            passengers=passengers,
            options=self._options(safe_mode, safe_origin, safe_destination, safe_date, passengers),
            source_notes=[
                "Compra final fuera de CEIBO hasta configurar medio de pago y confirmacion fuerte.",
                "Antes de pagar, revisar equipaje, horarios, escalas, terminal/aeropuerto y politicas de cambio.",
            ],
        )

    def extract_mode(self, normalized_message: str) -> str | None:
        for mode, aliases in self.mode_aliases.items():
            if any(alias in normalized_message for alias in aliases):
                return mode
        return None

    def extract_route(self, message: str, normalized_message: str) -> tuple[str | None, str | None]:
        patterns = [
            r"\b(?:de|desde)\s+(.+?)\s+(?:a|hasta|para)\s+(.+?)(?:\s+(?:el|para el|para|en)\s+\d|\s+mañana|\s+manana|\s+hoy|\s*$)",
            r"\b(?:a|hasta|para)\s+(.+?)\s+(?:desde|saliendo de)\s+(.+?)(?:\s+(?:el|para el|para|en)\s+\d|\s+mañana|\s+manana|\s+hoy|\s*$)",
        ]
        for index, pattern in enumerate(patterns):
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                first = self._clean_place(match.group(1))
                second = self._clean_place(match.group(2))
                if index == 0:
                    return first, second
                return second, first
        if " ida y vuelta " in normalized_message:
            return None, None
        return None, None

    def extract_date(self, message: str) -> str | None:
        normalized = project_knowledge_service.normalize(message)
        if "manana" in normalized:
            return "manana"
        if "hoy" in normalized:
            return "hoy"
        iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", message)
        if iso:
            return iso.group(1)
        numeric = re.search(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b", message)
        if numeric:
            return numeric.group(1)
        natural = re.search(r"\b(?:el|para el|para)\s+([0-9]{1,2}\s+de\s+[a-zA-ZáéíóúÁÉÍÓÚ]+)\b", message, flags=re.IGNORECASE)
        if natural:
            return natural.group(1)
        return None

    def extract_passengers(self, normalized_message: str) -> int:
        match = re.search(r"\b(\d{1,2})\s+(?:pasajeros|personas|adultos)\b", normalized_message)
        if match:
            return max(1, min(int(match.group(1)), 9))
        return 1

    def _options(
        self,
        mode: str,
        origin: str,
        destination: str,
        departure_date: str,
        passengers: int,
    ) -> list[TravelTicketOption]:
        providers = self._providers_for(mode)
        return [
            TravelTicketOption(
                mode=self.mode_labels.get(mode, mode),
                source=provider["source"],
                search_url=provider["url"](origin, destination, departure_date, passengers),
                booking_url=provider["url"](origin, destination, departure_date, passengers),
                note=provider["note"],
            )
            for provider in providers
        ]

    def _providers_for(self, mode: str) -> list[dict[str, object]]:
        if mode == "flight":
            return [
                self._provider("Google Flights", "https://www.google.com/travel/flights?q=vuelos+{origin}+a+{destination}+{date}", "comparador de vuelos"),
                self._provider("Skyscanner", "https://www.skyscanner.com/transport/flights/{origin}/{destination}/?adultsv2={passengers}", "comparador internacional"),
                self._provider("Despegar", "https://www.despegar.com.ar/shop/flights/results/oneway/{origin}/{destination}/{date}/{passengers}/0/0", "compra externa en Argentina/LatAm"),
            ]
        if mode == "bus":
            return [
                self._provider("Central de Pasajes", "https://www.centraldepasajes.com.ar/cdp/pasajes-micro/{origin}/{destination}", "micros Argentina"),
                self._provider("Plataforma 10", "https://www.plataforma10.com.ar/servicios/buscar-pasajes/{origin}/{destination}", "micros Argentina"),
                self._provider("Busbud", "https://www.busbud.com/en/search?origin={origin}&destination={destination}", "micros internacionales"),
            ]
        if mode == "train":
            return [
                self._provider("Trainline", "https://www.thetrainline.com/search?origin={origin}&destination={destination}", "trenes internacionales"),
                self._provider("Omio", "https://www.omio.com/search-frontend/results/{origin}/{destination}/{date}", "tren/bus/avion internacional"),
                self._provider("Trenes Argentinos", "https://webventas.sofse.gob.ar/", "trenes larga distancia Argentina"),
            ]
        if mode == "ferry":
            return [
                self._provider("Direct Ferries", "https://www.directferries.com/search.htm?query={origin}+{destination}", "ferries internacionales"),
                self._provider("Colonia Express", "https://www.coloniaexpress.com/ar", "ferry Rio de la Plata"),
                self._provider("Buquebus", "https://www.buquebus.com/", "ferry Rio de la Plata"),
            ]
        return [
            self._provider("Rome2Rio", "https://www.rome2rio.com/map/{origin}/{destination}", "rutas multimodales"),
            self._provider("Omio", "https://www.omio.com/search-frontend/results/{origin}/{destination}/{date}", "tren/bus/avion"),
            self._provider("Google Travel", "https://www.google.com/search?q=pasajes+{origin}+a+{destination}+{date}", "busqueda agregada"),
        ]

    def _provider(self, source: str, template: str, note: str) -> dict[str, object]:
        def build_url(origin: str, destination: str, date: str, passengers: int) -> str:
            return template.format(
                origin=quote_plus(origin),
                destination=quote_plus(destination),
                date=quote_plus(date),
                passengers=passengers,
            )

        return {"source": source, "url": build_url, "note": note}

    def _question_for_missing(
        self,
        missing: list[str],
        mode: str | None,
        origin: str | None,
        destination: str | None,
        departure_date: str | None,
    ) -> str:
        parts = []
        if not mode:
            parts.append("medio de transporte: avion, micro, tren, ferry o multimodal")
        if not origin:
            parts.append("origen")
        if not destination:
            parts.append("destino")
        if not departure_date:
            parts.append("fecha de salida")
        return "Para buscar pasajes necesito " + ", ".join(parts) + ". Ejemplo: vuelo de Buenos Aires a Madrid el 2026-08-12 para 1 pasajero."

    def _clean_place(self, value: str) -> str:
        cleaned = re.sub(r"\b(?:en|el|para|por|avion|vuelo|micro|bus|tren|ferry|pasaje|pasajes)\b", "", value, flags=re.IGNORECASE)
        return " ".join(cleaned.strip(" ?.!,").split()).title()


travel_booking_service = TravelBookingService()
