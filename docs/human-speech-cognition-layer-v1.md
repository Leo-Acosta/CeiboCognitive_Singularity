# Human Speech Cognition Layer v1

## Objetivo

Human Speech Cognition Layer v1 convierte transcripciones de habla humana en una traza cognitiva segura para CEIBO. La capa no escucha microfono real, no transcribe audio y no genera voz. Recibe texto ya transcripto, confianza estimada y metadatos simples, y prepara ese material para el Dialogue Orchestrator.

## Que Hace

- Normaliza la transcripcion.
- Registra idioma, fuente y confianza de transcripcion.
- Detecta senales debiles de habla: muletillas, pausas, urgencia, confusion y pedido de paso a paso.
- Clasifica claridad y ambiguedad.
- Decide si conviene entregar la solicitud al Dialogue Orchestrator o pedir repeticion.
- Alimenta Emotional State Layer solo con senales conversacionales debiles.
- Alimenta Cognitive Reflection Loop para aprendizaje interno.
- Produce un `spoken_response_plan` para que la respuesta escrita quede preparada para una futura voz hablada.

## Que No Hace

- No accede al microfono.
- No ejecuta ASR real.
- No sintetiza voz.
- No identifica al hablante por biometria.
- No infiere personalidad, diagnosticos, salud mental, identidad o intenciones ocultas desde la voz.
- No convierte emociones momentaneas en memoria autobiografica.
- No autoriza acciones fisicas o de sistema.

## `speech_cognition_trace`

La traza es minima y trazable:

- `raw_transcript`: texto recibido.
- `normalized_transcript`: texto normalizado para razonamiento.
- `transcription_confidence`: confianza de transcripcion.
- `speech_markers`: senales conversacionales, por ejemplo `explicit_confusion` o `step_by_step_request`.
- `clarity_level`: `clear`, `medium` o `low`.
- `ambiguity_level`: `low`, `medium` o `high`.
- `recommended_processing_mode`: `dialogue_orchestrator` o `request_repetition`.
- `safety_notes`: limites de seguridad cognitiva.

## `spoken_response_plan`

El plan de respuesta hablada no es audio. Es una guia para que CEIBO responda con forma apta para voz:

- estilo;
- ritmo;
- estructura;
- si debe resumir primero;
- si debe confirmar entendimiento;
- si debe evitar sobrecargar al usuario.

## Integracion

Flujo actual:

1. El chat recibe `message` y, opcionalmente, `metadata.speech_input`.
2. Human Speech Cognition Layer crea `speech_cognition_trace`.
3. Dialogue Orchestrator interpreta intencion, tono, riesgo y ruta cognitiva.
4. Emotional State Layer usa la traza de habla como senal debil, sin diagnosticar.
5. Spoken Response Planner genera `spoken_response_plan`.
6. Cognitive Reflection Loop usa la traza para aprender que falto y que debe mejorar.
7. Autobiographical Memory solo puede guardar preferencias u objetivos estables.

## Guardrails de Memoria

Se puede sugerir memoria si hay:

- preferencia persistente;
- objetivo de largo plazo;
- decision de proyecto;
- instruccion explicita de recordar;
- contenido no sensible y util para futuras conversaciones.

Se bloquea memoria si hay:

- baja confianza de transcripcion;
- emocion momentanea;
- frustracion pasajera;
- sarcasmo;
- datos sensibles;
- informacion intima;
- inferencia no confirmada;
- pedido de no recordar.

## Ejemplo Correcto

Entrada:

```json
{
  "message": "De ahora en adelante, cuando te hable por voz sobre errores, explicame despacio.",
  "metadata": {
    "speech_input": {
      "raw_transcript": "De ahora en adelante, cuando te hable por voz sobre errores, explicame despacio.",
      "transcription_confidence": 0.96,
      "source": "simulated_speech"
    }
  }
}
```

Resultado esperado:

- se interpreta como preferencia estable;
- se genera traza de habla clara;
- se permite recomendacion de memoria;
- se planifica respuesta breve y paso a paso.

## Ejemplo Incorrecto

Entrada:

```json
{
  "message": "eh no entiendo esto, arreglalo",
  "metadata": {
    "speech_input": {
      "raw_transcript": "eh no entiendo esto, arreglalo",
      "transcription_confidence": 0.45
    }
  }
}
```

Resultado esperado:

- no se guarda memoria;
- se pide confirmacion o repeticion;
- se evita inferir estado psicologico;
- se responde con baja carga cognitiva.

## Criterios Minimos de Seguridad Cognitiva

- La transcripcion dudosa se confirma antes de razonar fuerte.
- Las emociones detectadas por habla son senales debiles, no verdades.
- La memoria requiere estabilidad, utilidad y no sensibilidad.
- Toda traza debe ser compacta, auditable y no invasiva.
- La ejecucion real sigue dependiendo de sandbox, confirmacion y auditoria.
