from __future__ import annotations

from urllib.parse import urlparse

from ceibo_core.core.config import settings


class UnsafeOllamaHostError(Exception):
    pass


def _is_loopback_hostname(hostname: str) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    if host in ("localhost", "127.0.0.1", "[::1]"):
        return True
    return False


def _is_private_ip(hostname: str) -> bool:
    # quick checks for common LAN ranges
    if hostname.startswith("10."):
        return True
    if hostname.startswith("192.168."):
        return True
    if hostname.startswith("172."):
        # 172.16.0.0 - 172.31.255.255
        try:
            second = int(hostname.split(".")[1])
            return 16 <= second <= 31
        except Exception:
            return False
    return False


def validate_ollama_base_url(url: str) -> None:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname or ""

    if scheme not in ("http", ""):
        raise UnsafeOllamaHostError(
            "Ollama está configurado en un host inseguro. CEIBO solo permite Ollama en localhost/127.0.0.1 por defecto para evitar exposición del puerto 11434 y uso no autorizado."
        )

    if _is_loopback_hostname(hostname):
        return

    # allow 'localhost' without port, but block 0.0.0.0 and LAN/public IPs
    if hostname == "0.0.0.0":
        raise UnsafeOllamaHostError(
            "Ollama está configurado en un host inseguro. CEIBO solo permite Ollama en localhost/127.0.0.1 por defecto para evitar exposición del puerto 11434 y uso no autorizado."
        )

    if _is_private_ip(hostname):
        raise UnsafeOllamaHostError(
            "Ollama está configurado en un host inseguro. CEIBO solo permite Ollama en localhost/127.0.0.1 por defecto para evitar exposición del puerto 11434 y uso no autorizado."
        )

    # Block any other hostnames (public domains)
    raise UnsafeOllamaHostError(
        "Ollama está configurado en un host inseguro. CEIBO solo permite Ollama en localhost/127.0.0.1 por defecto para evitar exposición del puerto 11434 y uso no autorizado."
    )


def ollama_status(url: str) -> dict:
    safe = True
    message = "OK"
    try:
        validate_ollama_base_url(url)
    except UnsafeOllamaHostError as exc:
        safe = False
        message = str(exc)
    return {"ollama_base_url": url, "is_localhost": safe, "safe": safe, "message": message}
