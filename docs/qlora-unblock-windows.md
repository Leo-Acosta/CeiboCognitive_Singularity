# Desbloquear QLoRA En Windows

Estado detectado en esta maquina:

- Python QLoRA: `.venv-qlora`
- Dependencias instaladas: `torch`, `transformers`, `datasets`, `peft`, `accelerate`, `bitsandbytes`
- Dataset curado: `training/datasets/ceibo_instructions.curated.jsonl`
- Ejemplos curados actuales: 14
- PyTorch instalado: CPU
- CUDA visible para PyTorch: no
- `nvidia-smi`: no disponible en PATH
- `nvcc`: no disponible en PATH
- WSL: no instalado
- Docker: no disponible en PATH

## Bloqueo actual

QLoRA requiere GPU CUDA. El runner esta listo, pero el entrenamiento queda
`blocked` mientras PyTorch reporte:

```text
cuda_available False
device_count 0
```

## Comprobar entorno

```powershell
.\.venv-qlora\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda); print(torch.cuda.device_count())"
```

## Reintentar preflight

```powershell
.\.venv-qlora\Scripts\python.exe training\scripts\run_qlora.py --config training\configs\ceibo_qlora.local.json --preflight-only
```

## Reintentar entrenamiento smoke test

```powershell
.\.venv-qlora\Scripts\python.exe training\scripts\run_qlora.py --config training\configs\ceibo_qlora.local.json --max-steps 1
```

## Opciones para desbloquear

1. Instalar driver NVIDIA compatible y verificar `nvidia-smi`.
2. Instalar una build CUDA de PyTorch compatible con Python 3.13 y Windows.
3. Usar WSL2 + NVIDIA CUDA si prefieres entorno Linux.
4. Usar otra maquina con GPU y copiar este proyecto/dataset.

Cuando `torch.cuda.is_available()` sea `True`, el runner dejara de bloquearse
por `cuda_gpu` y podra iniciar el smoke test QLoRA.
