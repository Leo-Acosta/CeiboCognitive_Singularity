# Teacher Agent Local

CEIBO CORE puede usar Ollama con `mistral:latest` como Teacher IA local.

## Funcion

Mistral no entrena pesos por conversar. Su funcion es crear datos mejores:

1. Revisar respuestas de CEIBO.
2. Detectar problemas y fortalezas.
3. Proponer una respuesta ideal.
4. Guardar esa respuesta como ejemplo corregido.
5. Generar ejemplos sinteticos por tema.
6. Pasar esos ejemplos al curador de dataset.

Flujo:

```text
CEIBO responde
Teacher IA Mistral corrige
Dataset trainer guarda
Dataset curator filtra
Fine-tuning usa JSONL curado
```

## Requisitos

Ollama local:

```bash
ollama serve
ollama pull mistral
```

Variables:

```env
TEACHER_PROVIDER=ollama
TEACHER_BASE_URL=http://127.0.0.1:11434
TEACHER_MODEL=mistral:latest
TEACHER_TIMEOUT_SECONDS=600
```

## Endpoints

- `GET /api/v1/engine/teacher/status`
- `POST /api/v1/engine/teacher/review`
- `POST /api/v1/engine/teacher/synthetic-examples`

## Revisar una respuesta

```json
{
  "prompt": "Como entreno CEIBO CORE localmente?",
  "ceibo_response": "Usa un dataset y fine-tuning.",
  "expected_traits": ["pasos claros", "explicacion educativa"],
  "category": "training",
  "save_to_dataset": true
}
```

Si `save_to_dataset=true`, la respuesta ideal generada por Mistral queda
guardada como ejemplo `corrected` en el dataset operativo.

## Generar ejemplos

```json
{
  "topic": "automatizacion local con CEIBO CORE",
  "count": 3,
  "difficulty": "intermediate",
  "tags": ["teacher", "synthetic", "automation"],
  "save_to_dataset": true
}
```

Luego ejecuta:

```bash
python training/scripts/curate_dataset.py training/datasets/ceibo_instructions.jsonl --min-score 60
```
