# CEIBO AI Engine

CEIBO AI Engine es el motor IA local-first del proyecto.

## Principio

CEIBO no depende obligatoriamente de OpenAI ni Ollama. Esos proveedores pueden
existir como adaptadores, pero el camino principal es construir un motor propio:

- Codigo propio para orquestacion y razonamiento inicial.
- Memoria RAG local.
- Dataset propio en JSONL.
- Fine-tuning futuro con LoRA/QLoRA.
- Inferencia local en dispositivos propios.

## Directiva maestra

CEIBO CORE debe ayudar y ensenar a su usuario principal por todos los medios
permitidos y seguros. Cada respuesta debe facilitar el requerimiento recibido,
explicando cuando haga falta, guiando paso a paso cuando convenga y entregando
acciones concretas cuando el usuario pida ejecucion.

Esta directiva debe influir:

- El motor local.
- El orquestador.
- Los agentes.
- El dataset de entrenamiento.
- La evaluacion de respuestas futuras.

## Estado actual

- Provider por defecto: `ceibo_local`.
- Motor inicial: `ceibo-core-local-v0`.
- Modo: `rules+rag`.
- Entrenable: si.
- Dataset: `training/datasets/ceibo_instructions.jsonl`.

## Endpoints

- `GET /api/v1/engine/status`
- `POST /api/v1/engine/generate`
- `GET /api/v1/engine/models`
- `POST /api/v1/engine/models/recommend`
- `POST /api/v1/engine/training/plan`
- `GET /api/v1/engine/training/examples`
- `POST /api/v1/engine/training/examples`
- `POST /api/v1/engine/training/feedback`
- `GET /api/v1/engine/training/stats`
- `POST /api/v1/engine/training/curate/preview`
- `POST /api/v1/engine/training/curate/export`
- `GET /api/v1/engine/teacher/status`
- `POST /api/v1/engine/teacher/review`
- `POST /api/v1/engine/teacher/synthetic-examples`

## Camino hacia IA entrenada

1. Usar CEIBO local para generar y corregir respuestas.
2. Guardar ejemplos buenos como dataset.
3. Validar dataset con `training/scripts/prepare_dataset.py`.
4. Elegir un modelo base open-source local.
5. Ejecutar fine-tuning LoRA/QLoRA.
6. Servir el modelo entrenado con runtime local.
7. Conectar ese runtime al CEIBO AI Engine.

## Teacher IA local

Ollama con `mistral:latest` puede actuar como maestro local. Mistral revisa
respuestas de CEIBO, genera una respuesta ideal y produce ejemplos sinteticos.
Esos datos no entrenan por si solos: se guardan en JSONL, pasan por el curador y
luego alimentan el fine-tuning.

## Recolector de entrenamiento

El dashboard incluye un panel `Dataset trainer` para convertir conversaciones
reales en datos de entrenamiento:

- `Guardar buena`: guarda la ultima respuesta como ejemplo aprobado.
- `Guardar correccion`: guarda una version corregida y conserva la respuesta
  original en metadata.
- `GET /training/stats`: permite medir volumen, fuentes, tags y calidad del
  dataset antes de entrenar.

## Curador de dataset

Antes de fine-tuning, CEIBO puede analizar el JSONL operativo y generar un
dataset curado:

- Normaliza espacios, tags y campos principales.
- Descarta duplicados exactos.
- Penaliza respuestas demasiado cortas, genericas o temporales.
- Excluye ejemplos marcados como `bad`.
- Calcula score 0-100 por ejemplo.
- Exporta `training/datasets/ceibo_instructions.curated.jsonl`.

Comando:

```bash
python training/scripts/curate_dataset.py --min-score 60
```
