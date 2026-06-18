# Qwen 3B Smoke Test - Dataset Pack v0.1

## Objetivo

Probar rapido el pipeline de datasets y entrenamiento liviano antes de gastar
tiempo en Qwen 7B. No busca calidad final ni produccion.

## Modelo sugerido

`Qwen/Qwen2.5-3B-Instruct`

## Datasets

- `training/datasets/ceibo_core/curated.jsonl`
- `training/datasets/ceibo_legal/curated.jsonl`
- `training/datasets/ceibo_reverse_engineering/curated.jsonl`

## Validar JSONL

```powershell
python -c "import json,pathlib; [json.loads(l) for p in pathlib.Path('training/datasets').glob('ceibo_*/*.jsonl') for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; print('ok')"
```

## Preflight

Si el runner esta disponible:

```powershell
python training/scripts/run_qlora.py --config training/configs/ceibo_core_qwen3b_smoke.json --preflight-only
```

## QLoRA smoke

```powershell
python training/scripts/run_qlora.py --config training/configs/ceibo_core_qwen3b_smoke.json --max-steps 10
```

## Datos sensibles

No usar secretos, datos personales reales, expedientes reales, documentos
privados ni tecnologia no autorizada.

## Salidas

Guardar adaptador en `models/adapters/ceibo-core-conversational-qwen3b-smoke-v0.1`
o en storage externo si pesa demasiado. Registrar metricas y ejemplos de
respuesta.

## Comparacion

Comparar modelo base vs base + prompt vs base + RAG vs adaptador. Evaluar
naturalidad, seguridad, guardrails, estilo argentino y utilidad.

## Resultados esperados

Pequenas mejoras de estilo y estructura. No esperar dominio juridico completo
ni precision tecnica final.

## Limitaciones

Un smoke test puede sobreajustar, no cubre casos reales amplios y no reemplaza
evaluacion manual.

## Proximo paso

Ampliar datasets a 100 ejemplos por vertical y preparar Qwen 7B LoRA/QLoRA.
