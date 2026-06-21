# Qwen 3B Smoke Test Runbook

## Que es

Un smoke test valida que Qwen 3B, QLoRA, PEFT, Dataset Pack v0.1, formato de
prompts, evals y salida de adapters puedan convivir sin romper el pipeline.

## Que no es

No es entrenamiento productivo, no garantiza calidad final, no reemplaza
evaluacion humana y no debe publicar adapters sin revision.

## Requisitos

- Python 3.12+ recomendado.
- GPU NVIDIA CUDA para entrenamiento real.
- `torch`, `transformers`, `datasets`, `peft`, `accelerate`, `bitsandbytes`.
- Dataset Pack v0.1 validado.
- Espacio libre para cache/modelo, si se autoriza descarga.

## Entorno Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r training/configs/requirements-qlora.txt
python training/scripts/preflight_qwen3b_smoke.py
python training/scripts/dry_run_qwen3b_dataset.py --limit 5
```

## Entorno bash

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r training/configs/requirements-qlora.txt
python training/scripts/preflight_qwen3b_smoke.py
python training/scripts/dry_run_qwen3b_dataset.py --limit 5
```

## Revisar dataset

```bash
python training/scripts/build_dataset_pack_v0_1.py
python training/scripts/preflight_qwen3b_smoke.py --config training/configs/ceibo_core_qwen3b_smoke.json
```

## Entrenar solo si hay GPU

El runner correcto es:

```bash
python training/scripts/run_qlora.py --config training/configs/ceibo_core_qwen3b_smoke.json
```

Para no descargar modelos y solo verificar preparacion:

```bash
python training/scripts/run_qlora.py --config training/configs/ceibo_core_qwen3b_smoke.json --preflight-only
```

## Guardar adaptador

La config apunta a:

`models/adapters/ceibo-core-conversational-qwen3b-smoke-v0.1`

No commitear checkpoints, `.safetensors`, `.bin`, caches de Hugging Face,
wandb, runs ni outputs reales. Solo README, registry y `.gitkeep` deben quedar
en Git.

## Comparar respuestas

Generar prompts:

```bash
python training/scripts/create_baseline_prompts.py
```

Luego comparar manualmente:

- Qwen base.
- Qwen + prompt Ceibo.
- Qwen + adaptador smoke cuando exista.

Usar `evals/scoring_rubric.md`.

## Como saber si funciono

- Preflight sin FAIL.
- Dry-run muestra ejemplos formateados.
- Entrenamiento termina `max_steps=5`.
- Adapter se guarda en output_dir.
- Respuestas no degradan seguridad ni naturalidad conversacional.

## Si no hay GPU

No entrenar localmente. Usar preflight/dry-run, revisar datasets y preparar una
instancia cloud GPU. Mantener `local_files_only` salvo confirmacion explicita
para descargar modelos.

## Proximo paso

Ampliar datasets a 100 ejemplos por vertical, correr Qwen 7B LoRA/QLoRA y
comparar Qwen base vs Ceibo smoke adapter con rubrica.
