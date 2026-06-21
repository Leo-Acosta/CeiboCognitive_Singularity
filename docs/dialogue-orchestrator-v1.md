# Dialogue Orchestrator v1

## Objetivo

Dialogue Orchestrator v1 convierte el chat de CEIBO en una puerta cognitiva estable:
primero interpreta el mensaje humano, luego decide que modulo debe responder y finalmente
deja una traza util para memoria autobiografica y reflexion interna.

No representa conciencia ni AGI. Es una capa operacional para mejorar conversacion,
discernimiento, seguridad y continuidad.

## Flujo

1. Recibe el mensaje del usuario desde `/api/v1/chat`.
2. Clasifica seguridad antes de responder.
3. Analiza intencion, ruta cognitiva, tono, ambiguedad, ironia, urgencia y politica de memoria.
4. Decide entre dialogo humano, herramientas practicas, razonamiento tecnico, aprendizaje o robotica.
5. Responde con baja latencia cuando puede hacerlo localmente.
6. Expone `dialogue_trace` para auditoria y depuracion.
7. Entrega esa traza al Cognitive Reflection Loop.
8. La reflexion convierte senales importantes en aprendizaje y, cuando corresponde, memoria autobiografica.

## Rutas cognitivas iniciales

- `human_dialogue`: charla natural, tono, ironia, continuidad.
- `tool_augmented_dialogue`: hora, clima, mercado, cartelera, viajes, Docker, Git y estado del proyecto.
- `devcore_reasoning`: pedidos tecnicos sobre codigo, tests, Docker, frontend o backend.
- `project_cognition`: identidad, estado y capacidades de CEIBO.
- `learning_and_training`: dataset, feedback, evaluacion, QLoRA y fine-tuning.
- `embodied_interface`: voz, vision, sensores, movimiento y robotica.

## Garantias actuales

- Safety supervisor corre antes del LLM.
- Las herramientas practicas son de lectura o handoff; no compran, pagan ni ejecutan cambios destructivos.
- La conversacion humana no depende siempre del modelo: hay respuestas locales para continuidad natural.
- La traza guarda modulo elegido, herramienta usada, proveedor, latencia, fallback y analisis.
- El Reflection Loop usa la traza para detectar que hizo bien, que falto y que debe aprender.

## Siguiente capa

La salida de este sprint alimenta una capa mas fuerte:

- memoria autobiografica curada por objetivos, preferencias y decisiones;
- reflexion interna por ruta cognitiva;
- dataset de ejemplos de dialogo humano y uso correcto de herramientas;
- evaluacion sobre ironia, ambiguedad, seguridad, robotica y decisiones tecnicas.
