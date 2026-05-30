# Training Runner QLoRA

CEIBO CORE incluye un runner QLoRA para convertir el dataset curado en adapters
entrenables.

## Flujo

```text
Dataset operativo
  -> Dataset curator
  -> ceibo_instructions.curated.jsonl
  -> QLoRA preflight
  -> QLoRA training
  -> models/adapters/ceibo-core-mistral-qlora-v1
```

## Requisitos

QLoRA no puede entrenar directamente un modelo de Ollama/GGUF. Ollama Mistral
funciona como Teacher IA, pero el entrenamiento requiere un modelo base
compatible con HuggingFace/Transformers.

Dependencias:

```bash
pip install -r training/configs/requirements-qlora.txt
```

Tambien se requiere una GPU CUDA disponible para PyTorch.

Si existe `.venv-qlora`, el backend usara automaticamente ese Python para los
botones del dashboard.

## Preflight

```bash
python training/scripts/run_qlora.py --config training/configs/ceibo_qlora.local.json --preflight-only
```

El preflight revisa:

- dataset existente y no vacio
- dependencias Python
- CUDA disponible
- modelo base compatible con QLoRA
- manifiesto en `training/runs/<run_id>/manifest.json`

## Iniciar entrenamiento

```bash
python training/scripts/run_qlora.py --config training/configs/ceibo_qlora.local.json --max-steps 1
```

`max_steps=1` sirve como smoke test. Para entrenamiento real, aumenta ejemplos,
epochs y pasos.

## API

- `POST /api/v1/engine/training/qlora/preflight`
- `POST /api/v1/engine/training/qlora/start`
- `GET /api/v1/engine/training/qlora/jobs`
- `GET /api/v1/engine/training/qlora/jobs/{run_id}`
