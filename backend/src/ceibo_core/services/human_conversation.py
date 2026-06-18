from __future__ import annotations

from typing import List

from ceibo_core.core.config import settings
from ceibo_core.services.persona import build_persona_prompt
from ceibo_core.services.llm_gateway import llm_gateway
from ceibo_core.services.dialogue_memory import dialogue_memory_service
from ceibo_core.security.safety_supervisor import safety_supervisor


class HumanConversationService:
    async def respond(
        self,
        user_message: str,
        conversation_history: List[dict] | None = None,
        memory_context: str | None = None,
        mode: str = "human_persona",
    ) -> dict:
        # Safety check
        classification = safety_supervisor.classify(user_message)
        safety_checked = True
        if classification == "blocked_abuse":
            return {
                "response": "Leonardo, no puedo ayudar con esa solicitud porque parece abuso o daño real.",
                "safety_checked": True,
            }
        if classification == "sensitive_requires_confirmation":
            return {
                "response": "Leonardo, eso toca una zona sensible. Puedo ayudar en modo laboratorio defensivo o dar una explicación teórica. ¿Confirmás que querés proceder en modo laboratorio?",
                "safety_checked": True,
            }

        # Build system prompt
        memory_ctx = memory_context or (await dialogue_memory_service.get_relevant_memory_context(user_message))
        system_prompt = build_persona_prompt(memory_ctx, mode)

        # Build messages array
        messages: List[dict] = []
        messages.append({"role": "system", "content": system_prompt})
        # add recent history (limit to last 6)
        if conversation_history:
            for m in conversation_history[-6:]:
                role = m.get("role", "user")
                messages.append({"role": role, "content": m.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        # Call LLM gateway
        llm_resp = await llm_gateway.chat(messages=messages, temperature=0.7)

        # Optionally store memory for relationship-type notes
        if "prefiere" in user_message.lower() or "prefiero" in user_message.lower():
            await dialogue_memory_service.remember(
                kind="relationship_memory",
                title="Preferencias conversacionales de Leonardo",
                content=user_message,
                importance=80,
                tags=["leonardo", "preference"],
            )

        return {"response": llm_resp, "safety_checked": safety_checked}


human_conversation_service = HumanConversationService()
