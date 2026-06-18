# Ceibo AI Product Router

El router clasifica consultas en mode: core, legal, empleo, forense, code,
economics, finance, agents o general. Cada modo puede activar system prompt,
adaptador LoRA, RAG, herramientas, guardrails, evaluacion y template de salida.

El router no reemplaza la conversacion humana. Es una funcion interna de
Ceibo Core: el usuario sigue hablando con Ceibo Core, que mantiene tono natural,
preguntas aclaratorias, memoria y respuesta profesional.

## Reverse Engineering Mode

El router puede clasificar `mode: reverse_engineering`. Este modo activa
prompts, adaptador `ceibo_reverse_engineering_qwen7b_lora`, RAG
`ceibo_reverse_engineering`, herramientas de mapeo y guardrails:
`authorized_analysis_only`, `no_ip_infringement`, `no_drm_circumvention`,
`clean_room_required_for_reimplementation` y `no_malware_reproduction`.
