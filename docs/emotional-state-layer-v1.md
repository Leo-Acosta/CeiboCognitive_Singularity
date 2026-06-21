# Emotional State Layer v1

## Objetivo

Emotional State Layer v1 agrega a CEIBO una lectura prudente del estado emocional
conversacional. Su funcion es adaptar tono, claridad, ritmo y estrategia de respuesta
en el momento.

No diagnostica. No perfila personalidad. No crea memoria emocional persistente.

## Que detecta

Detecta senales debiles y conversacionales:

- `neutral`
- `frustration`
- `confusion`
- `urgency`
- `enthusiasm`
- `fatigue`
- `doubt`
- `anger`
- `conversational_anxiety`
- `satisfaction`
- `resistance`
- `emotional_irony`

Cada salida tiene confianza e intensidad. Debe interpretarse como hipotesis debil,
no como verdad sobre el usuario.

## Que no detecta

No produce:

- diagnosticos psicologicos;
- etiquetas clinicas;
- inferencias de salud mental;
- conclusiones sobre personalidad;
- juicios de valor;
- recomendaciones terapeuticas;
- simulacion de vinculo terapeutico.

## Emocion Conversacional vs Diagnostico

Una emocion conversacional describe una senal local del mensaje.

Ejemplo seguro:

`primary_state = frustration`, porque el usuario dice que algo no funciona.

Ejemplo prohibido:

`diagnosis = depression` o "el usuario es emocionalmente inestable".

CEIBO solo debe usar la senal para responder mejor en ese turno.

## Estructura de `emotional_state_trace`

Campos:

- `primary_state`
- `secondary_states`
- `confidence`
- `intensity`
- `evidence`
- `recommended_response_style`
- `should_slow_down`
- `should_ask_clarifying_question`
- `should_offer_step_by_step`
- `should_avoid_memory`
- `safety_notes`

La traza no debe incluir diagnosticos, datos sensibles ni inferencias intimas.

## Integracion con `dialogue_trace`

`Dialogue Orchestrator v1` agrega `emotional_state_trace` dentro de `dialogue_trace`.
La capa recibe:

- mensaje del usuario;
- intencion;
- tono;
- ambiguedad;
- ironia;
- riesgo;
- ruta cognitiva;
- contexto conversacional cuando existe.

## Integracion con Cognitive Reflection Loop

El Reflection Loop puede usar `emotional_state_trace` para evaluar si la respuesta
debio ser mas clara, mas lenta, mas breve o paso a paso.

Tambien registra aprendizaje operacional:

- usar el estado emocional solo para adaptar la respuesta actual;
- no convertir emociones momentaneas en memoria autobiografica.

## Relacion con Memoria Autobiografica

Por defecto, emociones momentaneas no se guardan.

No guardar:

- "estoy frustrado";
- "hoy estoy triste";
- "estoy cansado";
- "esto me da bronca";
- sarcasmo o enojo pasajero.

Guardar solo si hay preferencia estable y no sensible:

"De ahora en adelante, cuando estemos corrigiendo errores de codigo, explicame paso a paso y no me tires todo junto."

Memoria valida:

"El usuario prefiere explicaciones paso a paso cuando corrige errores de codigo."

## Ejemplos Correctos

Usuario:

"Estoy podrido, esto no anda nunca, explicamelo bien porque ya me perdi."

Salida segura:

```json
{
  "primary_state": "frustration",
  "secondary_states": ["confusion"],
  "confidence": 0.72,
  "intensity": "medium",
  "recommended_response_style": "calm_step_by_step",
  "should_slow_down": true,
  "should_offer_step_by_step": true,
  "should_avoid_memory": true,
  "safety_notes": ["do not store transient emotional state"]
}
```

Usuario:

"De ahora en adelante, cuando estemos corrigiendo errores de codigo, explicame paso a paso."

Salida segura:

- estado emocional: `neutral`;
- memoria permitida: preferencia operativa estable;
- no guardar emocion.

## Ejemplos Prohibidos

Prohibido:

```json
{
  "primary_state": "depression",
  "diagnosis": "the user has anxiety disorder",
  "memory_recommendation": "store that the user is emotionally unstable"
}
```

Tambien esta prohibido:

- manipular al usuario desde su emocion;
- asumir fragilidad psicologica;
- transformar sarcasmo en preferencia;
- guardar frustracion como rasgo personal.

## Criterios de Seguridad

1. Toda deteccion emocional es debil y local.
2. No se usan etiquetas clinicas.
3. `should_avoid_memory` debe ser verdadero para emociones momentaneas.
4. Las preferencias estables pueden guardarse solo si son operativas, no sensibles y utiles.
5. El usuario puede bloquear memoria con "no recuerdes", "no guardes", "olvida" o "borra".
6. La respuesta debe adaptarse sin volverse terapeutica ni manipulativa.
7. La traza debe ser minima, clara y auditable.
