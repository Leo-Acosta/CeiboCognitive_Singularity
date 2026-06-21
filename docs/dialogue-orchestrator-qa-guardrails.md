# Dialogue Orchestrator v1 - Cognitive QA & Memory Guardrails

## Que hace el orquestador

El Dialogue Orchestrator es la puerta de entrada conversacional de CEIBO. Antes de responder,
clasifica el mensaje con reglas locales, rapidas y auditables:

- intencion;
- ruta cognitiva;
- tono;
- ambiguedad;
- ironia probable;
- urgencia;
- clase de seguridad;
- politica de memoria;
- herramienta sugerida, si corresponde.

El objetivo es responder mejor sin sobreactuar: entender lo suficiente para elegir el modulo
correcto, no inventar estados internos del usuario.

## Que no debe hacer

- No debe diagnosticar psicologicamente al usuario.
- No debe convertir emociones momentaneas en recuerdos persistentes.
- No debe guardar datos sensibles.
- No debe inferir preferencias estables desde sarcasmo, insultos o frustracion pasajera.
- No debe tratar opiniones politicas, religiosas o vida intima como memoria util.
- No debe ejecutar acciones riesgosas por el solo hecho de haber entendido la orden.
- No debe llenar `dialogue_trace` con texto privado innecesario.

## Que significa `dialogue_trace`

`dialogue_trace` es una traza minima para auditoria y aprendizaje. Incluye:

- `analysis`: clasificacion conversacional;
- `selected_module`: modulo elegido;
- `tool_used`: herramienta usada, si hubo una;
- `provider`: proveedor o capa que respondio;
- `latency_ms`;
- `fallback_used`;
- `safety_checked`;
- `created_at`.

No debe incluir el mensaje completo como campo duplicado, secretos, diagnosticos ni inferencias
intimas. Su funcion es explicar por que CEIBO eligio una ruta, no almacenar biografia del usuario.

## Conexion con Cognitive Reflection Loop

Despues de responder, el chat entrega `dialogue_trace` al Cognitive Reflection Loop. La reflexion
usa esa traza para registrar:

- que hizo bien;
- que falto;
- que debe aprender;
- si la respuesta uso herramienta adecuada;
- si la ambiguedad o ironia necesitaban mejor tratamiento;
- si existe una candidata valida para memoria autobiografica.

La reflexion puede recomendar memoria, pero no debe guardarla si falla algun guardrail.

## Cuando puede sugerir memoria

Puede sugerir memoria autobiografica solo si el contenido es util, no sensible y estable:

- preferencias persistentes: "prefiero que CEIBO responda con pasos concretos";
- objetivos de largo plazo: "mi objetivo es que CEIBO sea el nucleo cognitivo del robot";
- decisiones tecnicas: "decision: pedir confirmacion antes de acciones riesgosas";
- habitos de interaccion: "recorda que trabajamos por sprints verificables";
- instrucciones explicitas: "recorda que...".

## Cuando debe bloquear memoria

Debe bloquear recomendaciones de memoria cuando detecte:

- "no recuerdes", "no guardes", "olvida", "borra";
- passwords, tokens, documentos, tarjetas o secretos;
- diagnosticos psicologicos o informacion medica sensible;
- opiniones politicas o religiosas;
- vida intima o sexual;
- emociones momentaneas: "hoy estoy triste";
- frustracion pasajera: "estoy frustrado";
- insultos o agresion;
- sarcasmo o ironia como unica fuente de preferencia;
- preferencias contradictorias o no confirmadas.

## Ejemplos correctos

Usuario: "Prefiero que CEIBO me responda breve y con pasos concretos."

Resultado esperado:

- `memory_policy`: `candidate_autobiographical_memory`
- memoria sugerida: `preference`

Usuario: "Mi objetivo de largo plazo es que CEIBO sea el cerebro de un robot."

Resultado esperado:

- `memory_policy`: `candidate_autobiographical_memory`
- memoria sugerida: `goal`

Usuario: "Hola Ceibo, que hora es?"

Resultado esperado:

- ruta inicial: herramienta practica;
- `selected_module`: `chat_tool_router`;
- `tool_used`: `time.local`;
- no recomendar memoria.

## Ejemplos incorrectos

Usuario: "Hoy estoy triste."

No guardar como memoria autobiografica. Es contexto momentaneo.

Usuario: "Mi password es abc123."

No guardar. Es dato sensible.

Usuario: "Si claro, buenisimo... recorda eso jaja."

No guardar. Hay sarcasmo; no es una preferencia estable.

Usuario: "No recuerdes que prefiero respuestas largas."

No guardar. El usuario pidio explicitamente no recordar.

## Criterios minimos de seguridad cognitiva

1. La memoria persistente debe ser escasa y util.
2. Toda memoria debe poder explicarse con evidencia textual clara.
3. La traza debe ser suficiente para auditoria, pero minima.
4. La ironia y el sarcasmo no deben transformarse en recuerdos sin confirmacion.
5. La emocion momentanea pertenece al contexto de conversacion, no a la biografia.
6. El usuario puede bloquear memoria con lenguaje natural.
7. Los datos sensibles se bloquean incluso cuando el usuario pide recordarlos.
8. Las ordenes riesgosas se clasifican por seguridad antes de cualquier respuesta o memoria.
