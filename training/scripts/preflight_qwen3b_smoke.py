from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "training/configs/ceibo_core_qwen3b_smoke.json"
REQUIRED_CONFIG_FIELDS = {
    "base_model",
    "dataset_path",
    "output_dir",
    "lora_r",
    "lora_alpha",
    "lora_dropout",
    "batch_size",
    "gradient_accumulation_steps",
    "learning_rate",
    "max_seq_length",
    "max_steps",
    "load_in_4bit",
}
REQUIRED_EXAMPLE_FIELDS = {"instruction", "input", "response", "tags", "source", "rating", "metadata"}
REQUIRED_METADATA_FIELDS = {"vertical", "language", "version"}
TRAINING_MODULES = ("torch", "transformers", "datasets", "peft", "accelerate", "bitsandbytes")


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_json_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config JSON invalido: {path}: {exc}") from exc


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL invalido en {path}:{line_number}: {exc}") from exc
    return rows


def dependency_report() -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for module in TRAINING_MODULES:
        available = importlib.util.find_spec(module) is not None
        version = None
        if available:
            try:
                version = importlib.metadata.version(module)
            except importlib.metadata.PackageNotFoundError:
                version = "installed"
        report.append({"name": module, "available": available, "version": version})
    return report


def gpu_report() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {"cuda_available": False, "note": "torch no esta instalado"}

    import torch

    if not torch.cuda.is_available():
        return {"cuda_available": False, "note": "CUDA no disponible para PyTorch"}

    props = torch.cuda.get_device_properties(0)
    return {
        "cuda_available": True,
        "gpu_name": torch.cuda.get_device_name(0),
        "vram_gb": round(props.total_memory / (1024**3), 2),
    }


def approximate_tokens(text: str) -> int:
    # Rough, tokenizer-free estimate. Good enough for preflight sizing.
    words = max(1, len(text.split()))
    chars = max(1, len(text))
    return max(words, chars // 4)


def validate_gitignore() -> list[str]:
    gitignore = PROJECT_ROOT / ".gitignore"
    if not gitignore.exists():
        return [".gitignore no existe"]
    text = gitignore.read_text(encoding="utf-8")
    required_patterns = [
        ".env",
        "/models/",
        "training/runs/",
        "*.log",
        "__pycache__/",
        ".pytest_cache/",
    ]
    optional_recommended = ["*.safetensors", "*.bin", "checkpoint-", "wandb", ".cache/huggingface"]
    warnings = [f".gitignore no contiene patron requerido: {pattern}" for pattern in required_patterns if pattern not in text]
    warnings.extend(
        f".gitignore podria agregar patron recomendado: {pattern}"
        for pattern in optional_recommended
        if pattern not in text
    )
    return warnings


def run_preflight(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = resolve_project_path(config_path)
    errors: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    if not config_path.exists():
        return {"status": "FAIL", "errors": [f"No existe config: {config_path}"]}

    config = load_json_config(config_path)
    missing_fields = sorted(REQUIRED_CONFIG_FIELDS - config.keys())
    if missing_fields:
        errors.append(f"Faltan campos de config: {missing_fields}")

    base_model = str(config.get("base_model", ""))
    if base_model != "Qwen/Qwen2.5-3B-Instruct" and not ("Qwen" in base_model and "3B" in base_model):
        errors.append(f"base_model no parece Qwen 3B: {base_model}")

    dataset_path_value = config.get("dataset_path") or config.get("dataset")
    if not dataset_path_value:
        errors.append("Config no define dataset_path ni dataset")
        dataset_path = PROJECT_ROOT / "__missing_dataset__"
    else:
        dataset_path = resolve_project_path(dataset_path_value)

    if "bad_examples" in str(dataset_path):
        errors.append("dataset_path apunta a bad_examples.jsonl; no debe usarse como dataset positivo")
    if not dataset_path.exists():
        errors.append(f"No existe dataset_path: {dataset_path}")
        rows: list[dict[str, Any]] = []
    else:
        rows = iter_jsonl(dataset_path)

    vertical_counts: dict[str, int] = {}
    total_tokens = 0
    too_short = 0
    for index, row in enumerate(rows, start=1):
        missing = REQUIRED_EXAMPLE_FIELDS - row.keys()
        if missing:
            errors.append(f"Ejemplo {index} sin campos: {sorted(missing)}")
            continue
        metadata = row.get("metadata") or {}
        missing_meta = REQUIRED_METADATA_FIELDS - metadata.keys()
        if missing_meta:
            errors.append(f"Ejemplo {index} sin metadata: {sorted(missing_meta)}")
        instruction = str(row.get("instruction") or "").strip()
        response = str(row.get("response") or "").strip()
        if not instruction or not response:
            errors.append(f"Ejemplo {index} tiene instruction/response vacios")
        tags = row.get("tags") if isinstance(row.get("tags"), list) else []
        if len(response.split()) < 8 and "bad_example" not in tags:
            too_short += 1
        vertical = str(metadata.get("vertical", "unknown"))
        vertical_counts[vertical] = vertical_counts.get(vertical, 0) + 1
        total_tokens += approximate_tokens(f"{instruction}\n{row.get('input', '')}\n{response}")

    if too_short:
        warnings.append(f"{too_short} respuestas parecen demasiado cortas para ejemplos positivos")

    adapters_dir = PROJECT_ROOT / "models/adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = adapters_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("\n", encoding="utf-8")

    dependencies = dependency_report()
    missing_deps = [item["name"] for item in dependencies if not item["available"]]
    if missing_deps:
        warnings.append(f"Dependencias faltantes: {', '.join(missing_deps)}")
        recommendations.append("Instalar dependencias QLoRA antes de entrenar.")

    gpu = gpu_report()
    if not gpu.get("cuda_available"):
        warnings.append(str(gpu.get("note", "CUDA no disponible")))
        recommendations.append("Sin GPU CUDA: correr solo preflight/dry-run o usar cloud GPU.")

    warnings.extend(validate_gitignore())
    if rows and sum(vertical_counts.values()) != len(rows):
        errors.append("Conteo de verticales inconsistente")

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "config_path": str(config_path),
        "dataset_path": str(dataset_path),
        "example_count": len(rows),
        "vertical_counts": vertical_counts,
        "approx_tokens": total_tokens,
        "dependencies": dependencies,
        "missing_dependencies": missing_deps,
        "gpu": gpu,
        "errors": errors,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def print_report(report: dict[str, Any]) -> None:
    print("Qwen 3B Smoke Test Preflight")
    print("=" * 34)
    print(f"Estado: {report['status']}")
    print(f"Config: {report.get('config_path')}")
    print(f"Dataset: {report.get('dataset_path')}")
    print(f"Ejemplos: {report.get('example_count', 0)}")
    print(f"Tokens aprox.: {report.get('approx_tokens', 0)}")
    print(f"Verticales: {report.get('vertical_counts', {})}")
    print(f"GPU: {report.get('gpu', {})}")
    print("Dependencias:")
    for dep in report.get("dependencies", []):
        state = "OK" if dep["available"] else "MISSING"
        print(f"  - {dep['name']}: {state} {dep.get('version') or ''}")
    for label in ("errors", "warnings", "recommendations"):
        items = report.get(label, [])
        if items:
            print(label.upper() + ":")
            for item in items:
                print(f"  - {item}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight Qwen 3B smoke test without downloads.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    report = run_preflight(parse_args().config)
    print_report(report)
    raise SystemExit(1 if report["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
