# CEIBO AI Training

Esta carpeta prepara el camino para entrenar/fine-tunear el motor local de CEIBO.

## Datasets incluidos

| Archivo | Uso |
| --- | --- |
| `datasets/ceibo_seed.jsonl` | Semilla base de identidad, memoria, agentes y entrenamiento. |
| `datasets/ceibo_seed.normalized.jsonl` | Semilla normalizada para pruebas de ingestion. |
| `datasets/ceibo_instructions.jsonl` | Dataset operativo capturado desde feedback/dashboard y ejemplos iniciales. |
| `datasets/ceibo_instructions.curated.jsonl` | Version curada para smoke tests de LoRA/QLoRA. |

## Objetivo

Crear datasets propios para convertir CEIBO CORE en una IA local ajustada a:

- Ayudar y ensenar a su usuario principal.
- Tu forma de trabajar.
- Automatizacion y agentes.
- Seguridad defensiva.
- Infraestructura.
- Memoria RAG.
- Control local y futuras capacidades multimodales.

## Formato JSONL

Cada linea debe ser un JSON independiente:

```json
{"instruction":"Explica tu arquitectura","input":"","response":"Soy CEIBO CORE...","tags":["core","architecture"]}
```

Campos:

- `instruction`: instruccion del usuario.
- `input`: contexto opcional.
- `response`: respuesta ideal de CEIBO.
- `tags`: etiquetas para filtrar ejemplos.
- `source`: origen del ejemplo (`manual`, `dashboard`, `api`).
- `rating`: calidad del ejemplo (`good`, `bad`, `corrected`) cuando proviene
  de feedback.
- `metadata`: datos auxiliares, como respuesta original antes de una correccion.

## Recoleccion desde el dashboard

El panel `Dataset trainer` permite guardar la ultima conversacion como dato de
entrenamiento:

- Usa `Guardar buena` cuando la respuesta de CEIBO ya sirve como ejemplo ideal.
- Usa `Guardar correccion` cuando quieras ensenar una version mejor.
- Revisa el contador del dataset para saber cuantos ejemplos operativos existen.

La API equivalente es:

- `POST /api/v1/engine/training/feedback`
- `GET /api/v1/engine/training/stats`

## Curacion previa a fine-tuning

Antes de entrenar, ejecuta el curador para limpiar y puntuar el dataset:

```bash
python training/scripts/curate_dataset.py --min-score 60
```

El curador:

- Valida cada linea JSONL.
- Normaliza textos y tags.
- Descarta duplicados exactos.
- Penaliza respuestas cortas o temporales.
- Excluye ejemplos con `rating=bad`.
- Exporta `datasets/ceibo_instructions.curated.jsonl`.

Desde la API:

- `POST /api/v1/engine/training/curate/preview`
- `POST /api/v1/engine/training/curate/export`

## Teacher IA con Ollama Mistral

Si tienes Ollama local con `mistral:latest`, CEIBO puede usarlo como maestro:

- Revisar respuestas de CEIBO.
- Crear respuestas ideales corregidas.
- Generar ejemplos sinteticos por tema.
- Guardar esos ejemplos en el dataset operativo.

Endpoints:

- `GET /api/v1/engine/teacher/status`
- `POST /api/v1/engine/teacher/review`
- `POST /api/v1/engine/teacher/synthetic-examples`

## Training Runner QLoRA

El runner QLoRA prepara y lanza fine-tuning local sobre un modelo base
Transformers/HuggingFace:

```bash
python training/scripts/run_qlora.py --config training/configs/ceibo_qlora.local.json --preflight-only
python training/scripts/run_qlora.py --config training/configs/ceibo_qlora.local.json --max-steps 1
```

Ollama Mistral sirve como Teacher IA, pero QLoRA necesita un modelo base
compatible con `transformers`, GPU CUDA y dependencias de entrenamiento.

## Flujo futuro

1. Recolectar ejemplos reales desde el dashboard o API.
2. Limpiar, puntuar y curar el dataset.
3. Elegir modelo base local.
4. Fine-tuning LoRA/QLoRA.
5. Exportar/adaptar el modelo a vLLM, llama.cpp u otro runtime local.
6. Conectar el modelo entrenado al `CEIBO AI Engine`.

## Archivos

- `datasets/ceibo_seed.jsonl`: ejemplos iniciales.
- `datasets/ceibo_instructions.jsonl`: dataset generado por API.
- `configs/ceibo_qlora.example.json`: configuracion ejemplo para entrenamiento futuro.
- `scripts/prepare_dataset.py`: validador y normalizador JSONL.

## Dataset Pack v0.1

El pack v0.1 agrega datasets SFT en JSONL para tres prioridades: Ceibo Core
Conversational, Ceibo Legal Laboral y Ceibo Ingenieria Inversa. Incluye
`seed.jsonl`, `curated.jsonl`, `bad_examples.jsonl`, `eval_cases.jsonl`,
rubrica, evals y una configuracion Qwen 3B smoke test.

Readiness pack:

```bash
python training/scripts/preflight_qwen3b_smoke.py
python training/scripts/dry_run_qwen3b_dataset.py --limit 5
python training/scripts/create_baseline_prompts.py
```
