# Flujo Para Modelo Local Entrenable

CEIBO CORE seguira dos caminos complementarios:

## Camino recomendado: fine-tuning local

Este es el camino practico para tener una IA local personalizada.

1. Elegir modelo base local open-source.
2. Crear dataset propio en JSONL.
3. Entrenar adapters LoRA/QLoRA.
4. Evaluar respuestas.
5. Servir el modelo localmente.
6. Conectar el runtime al CEIBO AI Engine.

Endpoints:

- `GET /api/v1/engine/models`
- `POST /api/v1/engine/models/recommend`
- `POST /api/v1/engine/training/plan`
- `POST /api/v1/engine/training/feedback`
- `GET /api/v1/engine/training/stats`
- `POST /api/v1/engine/training/curate/preview`
- `POST /api/v1/engine/training/curate/export`
- `GET /api/v1/engine/teacher/status`
- `POST /api/v1/engine/teacher/review`
- `POST /api/v1/engine/teacher/synthetic-examples`

### Dataset operativo

Antes de entrenar, CEIBO debe acumular ejemplos aprobados por el usuario:

1. Conversar con CEIBO desde el dashboard.
2. Guardar respuestas buenas como ejemplos `good`.
3. Corregir respuestas debiles como ejemplos `corrected`.
4. Revisar estadisticas del dataset por fuente, rating y tags.
5. Ejecutar limpieza y validacion del JSONL antes del fine-tuning.

### Curacion automatica

El curador transforma el dataset operativo en un dataset entrenable:

```bash
python training/scripts/curate_dataset.py --min-score 60
```

Produce `training/datasets/ceibo_instructions.curated.jsonl`, descartando
duplicados, registros invalidos y ejemplos debajo del score minimo.

### Teacher IA local

Ollama con Mistral puede generar y corregir ejemplos. Este flujo crea datos para
entrenar, pero no reemplaza el fine-tuning:

1. CEIBO responde.
2. Mistral revisa y genera respuesta ideal.
3. El ejemplo corregido se guarda en JSONL.
4. El curador filtra calidad.
5. QLoRA entrena con el dataset curado.

## Camino avanzado: entrenamiento desde cero

Entrenar un modelo competitivo desde cero requiere muchisimos datos, GPUs y tiempo.
CEIBO prepara un camino de investigacion para modelos pequenos propios:

1. Construir corpus propio.
2. Crear tokenizer.
3. Definir arquitectura pequena.
4. Pretraining desde cero.
5. Instruction tuning posterior.
6. Exportar a runtime local.

Esto sirve para aprendizaje, control total y experimentacion, no para competir al
inicio con modelos fundacionales grandes.
