from __future__ import annotations

import re
from urllib.parse import quote

import httpx

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import WeatherDailyForecast, WeatherForecast, WeatherObservation


WEATHER_CODE_LABELS = {
    0: "cielo despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "niebla",
    48: "niebla con escarcha",
    51: "llovizna leve",
    53: "llovizna moderada",
    55: "llovizna intensa",
    61: "lluvia leve",
    63: "lluvia moderada",
    65: "lluvia intensa",
    71: "nieve leve",
    73: "nieve moderada",
    75: "nieve intensa",
    80: "chaparrones leves",
    81: "chaparrones moderados",
    82: "chaparrones intensos",
    95: "tormenta",
}


class WeatherService:
    provider = "open-meteo"

    def extract_location(self, message: str) -> str | None:
        normalized = " ".join(message.strip().split())
        patterns = [
            r"\b(?:en|para|de)\s+([a-zA-ZÀ-ÿ\s.'-]{3,80})$",
            r"\bclima\s+([a-zA-ZÀ-ÿ\s.'-]{3,80})$",
            r"\btiempo\s+([a-zA-ZÀ-ÿ\s.'-]{3,80})$",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                location = match.group(1).strip(" ?.!,")
                if location and location.lower() not in {"hoy", "ahora", "actual"}:
                    return location
        return None

    async def current_weather(self, message: str, location: str | None = None) -> WeatherObservation:
        requested_location = location or self.extract_location(message) or settings.ceibo_default_weather_location
        if not requested_location:
            return WeatherObservation(
                status="missing_location",
                provider=self.provider,
                requires_location=True,
                error="Falta ciudad o ubicacion para consultar clima.",
            )

        try:
            place = await self._geocode(requested_location)
            if place is None:
                return WeatherObservation(
                    status="not_found",
                    provider=self.provider,
                    location=requested_location,
                    error="No pude resolver esa ubicacion.",
                )
            return await self._forecast(place)
        except httpx.HTTPError as exc:
            return WeatherObservation(
                status="provider_unavailable",
                provider=self.provider,
                location=requested_location,
                error=f"No pude conectar con el proveedor de clima: {exc.__class__.__name__}.",
            )

    async def daily_forecast(self, message: str, location: str | None = None, days: int = 5) -> WeatherForecast:
        requested_location = location or self.extract_location(message) or settings.ceibo_default_weather_location
        if not requested_location:
            return WeatherForecast(
                status="missing_location",
                provider=self.provider,
                requires_location=True,
                error="Falta ciudad o ubicacion para consultar pronostico.",
            )

        try:
            place = await self._geocode(requested_location)
            if place is None:
                return WeatherForecast(
                    status="not_found",
                    provider=self.provider,
                    location=requested_location,
                    error="No pude resolver esa ubicacion.",
                )
            return await self._daily_forecast(place, days=days)
        except httpx.HTTPError as exc:
            return WeatherForecast(
                status="provider_unavailable",
                provider=self.provider,
                location=requested_location,
                error=f"No pude conectar con el proveedor de clima: {exc.__class__.__name__}.",
            )

    async def _geocode(self, location: str) -> dict[str, object] | None:
        url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={quote(location)}&count=1&language=es&format=json"
        )
        async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results") or []
        if not results:
            return None
        return results[0]

    async def _forecast(self, place: dict[str, object]) -> WeatherObservation:
        latitude = float(place["latitude"])
        longitude = float(place["longitude"])
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            "&timezone=auto"
        )
        async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        current = payload.get("current") or {}
        code = current.get("weather_code")
        return WeatherObservation(
            status="ok",
            provider=self.provider,
            location=str(place.get("name") or ""),
            country=str(place.get("country") or ""),
            latitude=latitude,
            longitude=longitude,
            temperature_c=self._float_or_none(current.get("temperature_2m")),
            apparent_temperature_c=self._float_or_none(current.get("apparent_temperature")),
            humidity_percent=self._int_or_none(current.get("relative_humidity_2m")),
            wind_kmh=self._float_or_none(current.get("wind_speed_10m")),
            weather_code=self._int_or_none(code),
            condition=WEATHER_CODE_LABELS.get(self._int_or_none(code), "condicion no clasificada"),
            observed_at=str(current.get("time") or ""),
            source_url="https://open-meteo.com/",
        )

    async def _daily_forecast(self, place: dict[str, object], days: int) -> WeatherForecast:
        latitude = float(place["latitude"])
        longitude = float(place["longitude"])
        safe_days = max(1, min(days, 7))
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,precipitation_sum"
            f"&forecast_days={safe_days}"
            "&timezone=auto"
        )
        async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        codes = daily.get("weather_code") or []
        max_temps = daily.get("temperature_2m_max") or []
        min_temps = daily.get("temperature_2m_min") or []
        rain_probabilities = daily.get("precipitation_probability_max") or []
        precipitation = daily.get("precipitation_sum") or []
        forecasts = [
            WeatherDailyForecast(
                date=str(date),
                weather_code=self._int_or_none(self._at(codes, index)),
                condition=WEATHER_CODE_LABELS.get(
                    self._int_or_none(self._at(codes, index)),
                    "condicion no clasificada",
                ),
                temperature_min_c=self._float_or_none(self._at(min_temps, index)),
                temperature_max_c=self._float_or_none(self._at(max_temps, index)),
                precipitation_probability_max=self._int_or_none(self._at(rain_probabilities, index)),
                precipitation_mm=self._float_or_none(self._at(precipitation, index)),
            )
            for index, date in enumerate(dates)
        ]
        return WeatherForecast(
            status="ok",
            provider=self.provider,
            location=str(place.get("name") or ""),
            country=str(place.get("country") or ""),
            latitude=latitude,
            longitude=longitude,
            days=forecasts,
            source_url="https://open-meteo.com/",
        )

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        try:
            return round(float(value), 1)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _at(values: list[object], index: int) -> object | None:
        try:
            return values[index]
        except IndexError:
            return None


weather_service = WeatherService()
