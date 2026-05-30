import argparse
import importlib.metadata
import importlib.util
import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "training" / "configs" / "ceibo_qlora.local.json"
RUNS_DIR = PROJECT_ROOT / "training" / "runs"
REQUIRED_MODULES = ("torch", "transformers", "datasets", "peft", "accelerate", "bitsandbytes")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside project root: {resolved}") from exc
    return resolved


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def apply_overrides(config: dict, args: argparse.Namespace) -> dict:
    updated = dict(config)
    if args.base_model:
        updated["base_model"] = args.base_model
    if args.dataset:
        updated["dataset"] = args.dataset
    if args.output_dir:
        updated["output_dir"] = args.output_dir
    if args.max_steps is not None:
        updated["max_steps"] = args.max_steps
    if args.local_files_only is not None:
        updated["local_files_only"] = args.local_files_only
    return updated


def count_jsonl_examples(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            if line.strip():
                count += 1
    return count


def dependency_status() -> list[dict]:
    dependencies: list[dict] = []
    for name in REQUIRED_MODULES:
        available = importlib.util.find_spec(name) is not None
        version = None
        if available:
            try:
                version = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                version = "installed"
        dependencies.append(
            {
                "name": name,
                "available": available,
                "version": version,
                "required": True,
            }
        )
    return dependencies


def cuda_report() -> tuple[bool, str]:
    if importlib.util.find_spec("torch") is None:
        return False, "torch is not installed"
    import torch

    if not torch.cuda.is_available():
        return False, "CUDA GPU is not available to PyTorch"
    device_name = torch.cuda.get_device_name(0)
    memory_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    return True, f"{device_name} ({memory_gb} GB VRAM)"


def build_manifest(
    *,
    run_id: str,
    status: str,
    config_path: Path,
    config: dict,
    command: list[str],
    dependencies: list[dict],
    missing: list[str],
    warnings: list[str],
    started_at: str,
    completed_at: str | None = None,
    log_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    dataset_path = resolve_project_path(config["dataset"])
    output_dir = resolve_project_path(config["output_dir"])
    return {
        "run_id": run_id,
        "status": status,
        "config_path": str(config_path),
        "dataset_path": str(dataset_path),
        "output_dir": str(output_dir),
        "base_model": config["base_model"],
        "command": command,
        "dataset_examples": count_jsonl_examples(dataset_path),
        "dependencies": dependencies,
        "missing_requirements": missing,
        "warnings": warnings,
        "log_path": str(log_path) if log_path else None,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["manifest_path"] = str(path)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def preflight(
    *,
    run_id: str,
    config_path: Path,
    config: dict,
    command: list[str],
    started_at: str,
    manifest_path: Path,
    log_path: Path,
) -> dict:
    dependencies = dependency_status()
    missing = [item["name"] for item in dependencies if item["required"] and not item["available"]]
    warnings: list[str] = []
    dataset_path = resolve_project_path(config["dataset"])
    dataset_examples = count_jsonl_examples(dataset_path)

    if not dataset_path.exists():
        missing.append(f"dataset:{dataset_path}")
    elif dataset_examples == 0:
        missing.append("dataset_examples")
    elif dataset_examples < 50:
        warnings.append(
            f"Dataset pequeno: {dataset_examples} ejemplos. Sirve para smoke test, no para calidad real."
        )

    if ":" in str(config["base_model"]) and "/" not in str(config["base_model"]):
        missing.append("huggingface_base_model")
        warnings.append(
            "Un modelo de Ollama/GGUF no se puede fine-tunear con QLoRA directamente; "
            "usa un modelo base HuggingFace/Transformers compatible."
        )

    cuda_available, cuda_note = cuda_report()
    if not cuda_available:
        missing.append("cuda_gpu")
    warnings.append(cuda_note)

    status = "blocked" if missing else "ready"
    manifest = build_manifest(
        run_id=run_id,
        status=status,
        config_path=config_path,
        config=config,
        command=command,
        dependencies=dependencies,
        missing=sorted(set(missing)),
        warnings=warnings,
        started_at=started_at,
        completed_at=now_iso(),
        log_path=log_path,
        manifest_path=manifest_path,
    )
    write_manifest(manifest_path, manifest)
    return manifest


def load_training_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            instruction = str(record.get("instruction") or "").strip()
            response = str(record.get("response") or "").strip()
            if not instruction or not response:
                raise ValueError(f"Invalid training record at line {line_number}")
            input_text = str(record.get("input") or "").strip()
            prompt = instruction if not input_text else f"{instruction}\n\nContexto:\n{input_text}"
            records.append(
                {
                    "text": f"<s>[INST] {prompt} [/INST]\n{response}</s>",
                }
            )
    return records


def run_training(
    *,
    run_id: str,
    config_path: Path,
    config: dict,
    command: list[str],
    manifest_path: Path,
    log_path: Path,
) -> dict:
    started_at = now_iso()
    preflight_manifest = preflight(
        run_id=run_id,
        config_path=config_path,
        config=config,
        command=command,
        started_at=started_at,
        manifest_path=manifest_path,
        log_path=log_path,
    )
    if preflight_manifest["status"] == "blocked":
        return preflight_manifest

    output_dir = resolve_project_path(config["output_dir"])
    dataset_path = resolve_project_path(config["dataset"])
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = dict(preflight_manifest)
    manifest["status"] = "running"
    manifest["completed_at"] = None
    write_manifest(manifest_path, manifest)

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        Trainer,
        TrainingArguments,
    )

    records = load_training_records(dataset_path)
    dataset = Dataset.from_list(records)
    tokenizer = AutoTokenizer.from_pretrained(
        config["base_model"],
        local_files_only=bool(config.get("local_files_only", False)),
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    max_seq_length = int(config.get("max_seq_length", 2048))

    def tokenize(batch: dict) -> dict:
        tokenized = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_seq_length,
            padding="max_length",
        )
        tokenized["labels"] = list(tokenized["input_ids"])
        return tokenized

    tokenized_dataset = dataset.map(tokenize, remove_columns=["text"])
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        config["base_model"],
        quantization_config=quantization_config,
        device_map="auto",
        local_files_only=bool(config.get("local_files_only", False)),
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(
        r=int(config.get("lora_rank", 16)),
        lora_alpha=int(config.get("lora_alpha", 32)),
        target_modules=config.get(
            "target_modules",
            ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        ),
        lora_dropout=float(config.get("lora_dropout", 0.05)),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 4)),
        learning_rate=float(config.get("learning_rate", 2e-4)),
        num_train_epochs=float(config.get("epochs", 1)),
        max_steps=int(config["max_steps"]) if config.get("max_steps") else -1,
        logging_steps=int(config.get("logging_steps", 1)),
        save_steps=int(config.get("save_steps", 25)),
        fp16=True,
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    manifest["status"] = "completed"
    manifest["completed_at"] = now_iso()
    write_manifest(manifest_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CEIBO CORE QLoRA fine-tuning.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--local-files-only", dest="local_files_only", action="store_true")
    parser.add_argument("--allow-download", dest="local_files_only", action="store_false")
    parser.set_defaults(local_files_only=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = resolve_project_path(args.config)
    config = apply_overrides(load_config(config_path), args)
    run_id = args.run_id or f"qlora-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    manifest_path = run_dir / "manifest.json"
    log_path = run_dir / "train.log"
    command = [sys.executable, *sys.argv]
    started_at = now_iso()

    try:
        if args.preflight_only:
            manifest = preflight(
                run_id=run_id,
                config_path=config_path,
                config=config,
                command=command,
                started_at=started_at,
                manifest_path=manifest_path,
                log_path=log_path,
            )
        else:
            run_dir.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as log_file:
                log_file.write(f"CEIBO QLoRA run {run_id}\n")
                try:
                    manifest = run_training(
                        run_id=run_id,
                        config_path=config_path,
                        config=config,
                        command=command,
                        manifest_path=manifest_path,
                        log_path=log_path,
                    )
                except Exception:
                    log_file.write(traceback.format_exc())
                    raise
    except Exception as exc:
        manifest = build_manifest(
            run_id=run_id,
            status="failed",
            config_path=config_path,
            config=config,
            command=command,
            dependencies=dependency_status(),
            missing=[],
            warnings=[str(exc)],
            started_at=started_at,
            completed_at=now_iso(),
            log_path=log_path,
            manifest_path=manifest_path,
        )
        write_manifest(manifest_path, manifest)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        raise SystemExit(1) from exc

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    raise SystemExit(2 if manifest["status"] == "blocked" else 0)


if __name__ == "__main__":
    main()
