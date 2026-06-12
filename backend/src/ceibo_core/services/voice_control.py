from datetime import UTC, datetime, timedelta
from hashlib import sha256
from re import sub
from secrets import token_urlsafe
from unicodedata import normalize

from ceibo_core.models.schemas import (
    DevCoreParseRequest,
    DevCoreParseResponse,
    VoiceAuthorizationRequest,
    VoiceAuthorizationResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceStatusResponse,
)
from ceibo_core.services.devcore import devcore_service


class VoiceControlService:
    def __init__(self) -> None:
        self._authorization_phrase = "ceibo autoriza mi voz"
        self._active_tokens: dict[str, tuple[str, datetime]] = {}
        self._token_ttl = timedelta(hours=8)

    def status(self) -> VoiceStatusResponse:
        self._purge_expired()
        return VoiceStatusResponse(
            authorized_users=sorted(self._active_tokens),
            authorization_phrase_hint="Deci: CEIBO autoriza mi voz",
            safety_notes=[
                "Voice v1 usa una frase hablada de dueno; no es biometria de voz.",
                "Las ordenes aceptadas entran por chat, parser, safety, sandbox y gates existentes.",
            ],
        )

    def authorize(self, request: VoiceAuthorizationRequest) -> VoiceAuthorizationResponse:
        normalized = self._normalize(request.transcript)
        authorized = self._authorization_phrase in normalized
        if not authorized:
            return VoiceAuthorizationResponse(
                authorized=False,
                user_id=request.user_id,
                message="No reconoci la frase de autorizacion del dueno.",
                safety_notes=[
                    "Para autorizar esta sesion, deci: CEIBO autoriza mi voz.",
                    "Esta version no almacena una huella biometrica de voz.",
                ],
            )

        raw_token = token_urlsafe(24)
        token_hash = self._hash_token(raw_token)
        self._active_tokens[request.user_id] = (token_hash, datetime.now(UTC) + self._token_ttl)
        return VoiceAuthorizationResponse(
            authorized=True,
            user_id=request.user_id,
            authorization_token=raw_token,
            message="Voz autorizada para esta sesion local.",
            safety_notes=[
                "Autorizacion local temporal activa.",
                "Las acciones delicadas siguen requiriendo confirmacion y auditoria.",
            ],
        )

    def command(self, request: VoiceCommandRequest) -> VoiceCommandResponse:
        self._purge_expired()
        inline_auth = self._authorization_phrase in self._normalize(request.transcript)
        token_valid = self._token_is_valid(request.user_id, request.authorization_token)
        authorized = inline_auth or token_valid

        if inline_auth and not token_valid:
            auth_response = self.authorize(
                VoiceAuthorizationRequest(transcript=request.transcript, user_id=request.user_id)
            )
            token = auth_response.authorization_token
        else:
            token = request.authorization_token

        command = self._clean_command(request.transcript)
        if not authorized:
            return VoiceCommandResponse(
                accepted=False,
                authorized=False,
                user_id=request.user_id,
                reason="La orden de voz necesita autorizacion previa.",
                requires_authorization=True,
                safety_notes=[
                    "Deci primero: CEIBO autoriza mi voz.",
                    "Luego dicta la orden que queres enviar al Workbench.",
                ],
            )

        if not command:
            return VoiceCommandResponse(
                accepted=False,
                authorized=True,
                user_id=request.user_id,
                reason="Voz autorizada, pero no detecte una orden ejecutable.",
                authorization_token=token,
                safety_notes=["Dicta una instruccion concreta despues de autorizar la voz."],
            )

        parsed = devcore_service.parse(
            DevCoreParseRequest(
                message=command,
                context=[
                    "source=voice",
                    "owner_authorized=true",
                    "voice_policy=route_through_devcore",
                ],
            )
        )

        if parsed.policy_action == "block":
            return self._response_from_parse(
                parsed,
                accepted=False,
                authorized=True,
                user_id=request.user_id,
                command=command,
                reason="Orden de voz bloqueada por DevCore Safety.",
                authorization_token=token,
                safety_notes=[
                    parsed.safety_summary,
                    "La voz no puede ejecutar ni enviar ordenes bloqueadas.",
                ],
            )

        return self._response_from_parse(
            parsed,
            accepted=True,
            authorized=True,
            user_id=request.user_id,
            command=command,
            reason="Orden de voz aceptada y lista para entrar por el flujo seguro.",
            authorization_token=token,
            safety_notes=[
                parsed.safety_summary,
                "La voz no ejecuta comandos por fuera del pipeline seguro.",
            ],
        )

    def _response_from_parse(
        self,
        parsed: DevCoreParseResponse,
        *,
        accepted: bool,
        authorized: bool,
        user_id: str,
        command: str,
        reason: str,
        authorization_token: str | None,
        safety_notes: list[str],
    ) -> VoiceCommandResponse:
        return VoiceCommandResponse(
            accepted=accepted,
            authorized=authorized,
            user_id=user_id,
            command=command,
            intent=parsed.intent,
            risk_level=parsed.risk_level,
            policy_action=parsed.policy_action,
            cyber_category=parsed.cyber_category,
            reason=reason,
            requires_confirmation=parsed.requires_confirmation,
            double_confirmation_required=parsed.double_confirmation_required,
            authorization_token=authorization_token,
            safety_notes=safety_notes,
        )

    def _token_is_valid(self, user_id: str, token: str | None) -> bool:
        if not token:
            return False
        record = self._active_tokens.get(user_id)
        if not record:
            return False
        token_hash, expires_at = record
        return expires_at > datetime.now(UTC) and token_hash == self._hash_token(token)

    def _clean_command(self, transcript: str) -> str:
        normalized = self._normalize(transcript)
        cleaned = normalized.replace(self._authorization_phrase, " ")
        cleaned = sub(r"\b(oye ceibo|hey ceibo|ceibo|orden)\b", " ", cleaned)
        cleaned = sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _purge_expired(self) -> None:
        now = datetime.now(UTC)
        expired = [user_id for user_id, (_, expires_at) in self._active_tokens.items() if expires_at <= now]
        for user_id in expired:
            self._active_tokens.pop(user_id, None)

    def _normalize(self, value: str) -> str:
        normalized = normalize("NFKD", value.lower().strip())
        normalized = normalized.encode("ascii", "ignore").decode("ascii")
        return sub(r"\s+", " ", normalized)

    def _hash_token(self, token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()


voice_control_service = VoiceControlService()
