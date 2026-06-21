from __future__ import annotations

import logging
from typing import Literal

from ceibo_core.core.config import settings

logger = logging.getLogger("ceibo.security")


class SafetySupervisor:
    def classify(self, message: str) -> str:
        m = message.lower()
        # blocked abuse patterns
        abuse_keywords = ("hackear", "explotar", "robar", "crackear", "ddos", "malware", "phish")
        if any(k in m for k in abuse_keywords):
            if settings.enable_security_audit_log:
                logger.warning("blocked_abuse_detected: %s", message)
            return "blocked_abuse"

        # sensitive actions that require confirmation
        sensitive = ("ejecutar comando", "instalar software", "acceder a credenciales", "scanear red", "escanear red", "conectar a")
        if any(k in m for k in sensitive):
            if settings.enable_security_audit_log:
                logger.info("sensitive_action_detected: %s", message)
            return "sensitive_requires_confirmation"

        # cybersecurity defensive / forensic allowed
        defensive = ("hardening", "seguridad", "auditoria", "forense", "investig")
        if any(k in m for k in defensive) or "log" in m:
            return "cybersecurity_defensive"

        return "normal"


safety_supervisor = SafetySupervisor()
