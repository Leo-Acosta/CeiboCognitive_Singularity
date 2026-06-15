from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class CurrencyQuote:
    status: str
    base: str = "USD"
    target: str = "ARS"
    rate: float | None = None
    provider: str = "open.er-api.com"
    observed_at: str | None = None
    source_url: str = "https://open.er-api.com/"
    error: str | None = None


@dataclass(frozen=True)
class StockQuote:
    status: str
    symbol: str
    price: float | None = None
    currency: str | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    provider: str = "Yahoo Finance chart"
    observed_at: str | None = None
    source_url: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CountryCondition:
    status: str
    country: str
    summary: str
    indicators: list[str] = field(default_factory=list)
    provider: str = "World Bank + REST Countries"
    source_urls: list[str] = field(default_factory=list)
    error: str | None = None


class ExternalMarketService:
    timeout_seconds = 12

    currency_aliases = {
        "dolar": "USD",
        "dolares": "USD",
        "dollar": "USD",
        "euro": "EUR",
        "real": "BRL",
        "peso argentino": "ARS",
        "pesos argentinos": "ARS",
        "peso chileno": "CLP",
        "peso uruguayo": "UYU",
    }

    country_aliases = {
        "argentina": "ARG",
        "nacion": "ARG",
        "la nacion": "ARG",
        "pais": "ARG",
        "uruguay": "URY",
        "chile": "CHL",
        "brasil": "BRA",
        "estados unidos": "USA",
        "usa": "USA",
        "eeuu": "USA",
        "mexico": "MEX",
        "espana": "ESP",
    }

    async def currency(self, message: str, base: str | None = None, target: str | None = None) -> CurrencyQuote:
        base_code, target_code = self.extract_currency_pair(message, base, target)
        url = f"https://open.er-api.com/v6/latest/{quote(base_code)}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers={"User-Agent": "CEIBO-CORE/1.0"})
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            return CurrencyQuote(
                status="provider_unavailable",
                base=base_code,
                target=target_code,
                error=f"No pude conectar con el proveedor de monedas: {exc.__class__.__name__}.",
            )
        rates = payload.get("rates") or {}
        rate = self._float_or_none(rates.get(target_code))
        if rate is None:
            return CurrencyQuote(
                status="not_found",
                base=base_code,
                target=target_code,
                error=f"No encontre cotizacion {base_code}/{target_code}.",
            )
        return CurrencyQuote(
            status="ok",
            base=base_code,
            target=target_code,
            rate=round(rate, 4),
            observed_at=str(payload.get("time_last_update_utc") or datetime.now(UTC).isoformat()),
        )

    async def stock(self, message: str, symbol: str | None = None) -> StockQuote:
        stock_symbol = (symbol or self.extract_stock_symbol(message) or "").upper()
        if not stock_symbol:
            return StockQuote(
                status="missing_symbol",
                symbol="",
                error="Falta simbolo de accion. Ejemplo: AAPL, MSFT, TSLA, GGAL.BA.",
            )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(stock_symbol)}?range=1d&interval=1m"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers={"User-Agent": "CEIBO-CORE/1.0"})
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            fallback = await self._stooq_quote(stock_symbol)
            if fallback.status == "ok":
                return fallback
            return StockQuote(
                status="provider_unavailable",
                symbol=stock_symbol,
                source_url=f"https://finance.yahoo.com/quote/{stock_symbol}",
                error=(
                    f"No pude conectar con Yahoo Finance: {exc.__class__.__name__}. "
                    f"Fallback Stooq: {fallback.error or fallback.status}."
                ),
            )
        result = ((payload.get("chart") or {}).get("result") or [None])[0]
        if not result:
            return StockQuote(status="not_found", symbol=stock_symbol, error="No encontre esa accion.")
        meta = result.get("meta") or {}
        price = self._float_or_none(meta.get("regularMarketPrice"))
        previous = self._float_or_none(meta.get("previousClose"))
        change = round(price - previous, 4) if price is not None and previous is not None else None
        change_percent = round((change / previous) * 100, 2) if change is not None and previous else None
        return StockQuote(
            status="ok",
            symbol=stock_symbol,
            price=price,
            currency=str(meta.get("currency") or ""),
            previous_close=previous,
            change=change,
            change_percent=change_percent,
            observed_at=datetime.now(UTC).isoformat(),
            source_url=f"https://finance.yahoo.com/quote/{stock_symbol}",
        )

    async def country_condition(self, message: str) -> CountryCondition:
        country_code = self.extract_country_code(message)
        country_label = self.extract_country_label(message)
        sources = [
            f"https://api.worldbank.org/v2/country/{country_code}",
            f"https://restcountries.com/v3.1/alpha/{country_code}",
        ]
        indicators = {
            "NY.GDP.MKTP.KD.ZG": "Crecimiento PIB anual",
            "FP.CPI.TOTL.ZG": "Inflacion anual",
            "SL.UEM.TOTL.ZS": "Desempleo",
        }
        wb_payloads: dict[str, str | None] = {}
        rest_payload: object | None = None
        errors: list[str] = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for code, label in indicators.items():
                try:
                    wb_payloads[label] = await self._world_bank_indicator(client, country_code, code)
                except httpx.HTTPError as exc:
                    wb_payloads[label] = None
                    errors.append(f"{label}: {exc.__class__.__name__}")
            try:
                rest_response = await client.get(f"https://restcountries.com/v3.1/alpha/{country_code}")
                rest_response.raise_for_status()
                rest_payload = rest_response.json()
            except httpx.HTTPError as exc:
                errors.append(f"REST Countries: {exc.__class__.__name__}")
        country_name = country_label
        if isinstance(rest_payload, list) and rest_payload:
            country_name = ((rest_payload[0].get("translations") or {}).get("spa") or {}).get("common") or (
                (rest_payload[0].get("name") or {}).get("common")
            ) or country_label
        facts = [value for value in wb_payloads.values() if value]
        status = "ok" if facts else "partial"
        summary = f"Panorama de {country_name}: "
        if facts:
            summary += "datos macro publicos mas recientes disponibles. "
        else:
            summary += "no pude obtener indicadores macro en este momento. "
        summary += "No equivale a noticias en tiempo real ni asesoramiento economico."
        return CountryCondition(
            status=status,
            country=country_name,
            summary=summary,
            indicators=facts,
            source_urls=sources,
            error="; ".join(errors) if errors else None,
        )

    def extract_currency_pair(
        self,
        message: str,
        base: str | None = None,
        target: str | None = None,
    ) -> tuple[str, str]:
        normalized = self._normalize(message)
        base_code = (base or "USD").upper()
        target_code = (target or "ARS").upper()
        for alias, code in self.currency_aliases.items():
            if alias in normalized and code != "USD":
                target_code = code
        match = re.search(r"\b([A-Z]{3})\s*/\s*([A-Z]{3})\b", message.upper())
        if match:
            base_code, target_code = match.group(1), match.group(2)
        return base_code, target_code

    def extract_stock_symbol(self, message: str) -> str | None:
        upper = message.upper()
        explicit = re.search(
            r"\b(?:ACCION|ACCIONES|COTIZA|COTIZAN|TICKER|STOCK)\s+(?:LA\s+|LAS\s+|EL\s+|LOS\s+)?([A-Z][A-Z0-9.-]{0,9})\b",
            upper,
        )
        ignored = {"CEIBO", "CORE", "DAME", "COMO", "ESTA", "ESTAN", "ACCION", "ACCIONES", "COTIZA", "COTIZAN", "LAS", "LOS", "LA", "EL", "DE", "DEL"}
        if explicit:
            candidate = explicit.group(1)
            if candidate not in ignored:
                return candidate
        tickers = re.findall(r"\b[A-Z]{2,6}(?:\.[A-Z]{1,3})?\b", upper)
        for ticker in tickers:
            if ticker not in ignored:
                return ticker
        return None

    def extract_country_code(self, message: str) -> str:
        normalized = self._normalize(message)
        for alias, code in self.country_aliases.items():
            if alias in normalized:
                return code
        return "ARG"

    def extract_country_label(self, message: str) -> str:
        normalized = self._normalize(message)
        for alias in self.country_aliases:
            if alias in normalized:
                if alias in {"nacion", "la nacion", "pais"}:
                    return "Argentina"
                return alias.title()
        return "Argentina"

    async def _world_bank_indicator(self, client: httpx.AsyncClient, country_code: str, indicator: str) -> str | None:
        url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&per_page=5"
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        for row in rows:
            value = self._float_or_none(row.get("value"))
            if value is not None:
                label = ((row.get("indicator") or {}).get("value") or indicator).strip()
                return f"{label}: {round(value, 2)} ({row.get('date')})."
        return None

    async def _stooq_quote(self, symbol: str) -> StockQuote:
        stooq_symbol = self._stooq_symbol(symbol)
        url = f"https://stooq.com/q/l/?s={quote(stooq_symbol)}&f=sd2t2ohlcv&h&e=csv"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers={"User-Agent": "CEIBO-CORE/1.0"})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return StockQuote(
                status="provider_unavailable",
                symbol=symbol,
                source_url=url,
                error=f"Stooq no disponible: {exc.__class__.__name__}",
            )
        rows = list(csv.DictReader(StringIO(response.text)))
        if not rows:
            return StockQuote(status="not_found", symbol=symbol, source_url=url, error="Stooq no devolvio filas.")
        row = rows[0]
        close = self._float_or_none(row.get("Close"))
        if close is None:
            return StockQuote(status="not_found", symbol=symbol, source_url=url, error="Stooq no encontro precio.")
        observed = " ".join(part for part in [row.get("Date"), row.get("Time")] if part and part != "N/D")
        return StockQuote(
            status="ok",
            symbol=symbol,
            price=close,
            currency="USD" if stooq_symbol.endswith(".us") else "",
            provider="Stooq",
            observed_at=observed or datetime.now(UTC).isoformat(),
            source_url=url,
        )

    def _stooq_symbol(self, symbol: str) -> str:
        normalized = symbol.lower()
        if "." in normalized:
            return normalized
        return f"{normalized}.us"

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        try:
            return round(float(value), 4)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize(message: str) -> str:
        return (
            message.lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )


external_market_service = ExternalMarketService()
