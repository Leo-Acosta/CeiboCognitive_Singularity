from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "training" / "scripts"
CONFIG_PATH = REPO_ROOT / "training" / "configs" / "ceibo_core_qwen3b_smoke.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_qwen3b_smoke_config_is_valid_and_fast():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["base_model"] == "Qwen/Qwen2.5-3B-Instruct"
    assert config["dataset_path"] == "training/datasets/combined/ceibo_dataset_pack_v0.1.curated.jsonl"
    assert config["output_dir"].startswith("models/adapters/")
    assert config["max_steps"] <= 10
    assert config["lora_r"] == 8
    assert config["preserve_natural_dialogue"] is True
    assert config["intended_use"] == "smoke_test_only"


def test_qwen3b_dataset_path_exists_and_jsonl_is_valid():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset_path = REPO_ROOT / config["dataset_path"]
    rows = read_jsonl(dataset_path)

    assert dataset_path.exists()
    assert rows
    for row in rows:
        assert {"instruction", "input", "response", "tags", "source", "rating", "metadata"}.issubset(row)
        assert row["rating"] >= 4
        assert "bad_example" not in row["tags"]
        assert {"vertical", "language", "version"}.issubset(row["metadata"])


def test_qwen3b_dataset_preserves_core_dialogue_metadata():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    rows = read_jsonl(REPO_ROOT / config["dataset_path"])
    core_rows = [row for row in rows if row["metadata"]["vertical"] == "ceibo_core"]

    assert core_rows
    assert all(row["metadata"]["preserve_natural_dialogue"] is True for row in core_rows)


def test_qwen3b_scripts_import_without_training_side_effects():
    sys.path.insert(0, str(SCRIPTS_DIR))
    for script_name in [
        "preflight_qwen3b_smoke.py",
        "dry_run_qwen3b_dataset.py",
        "create_baseline_prompts.py",
        "build_dataset_pack_v0_1.py",
    ]:
        path = SCRIPTS_DIR / script_name
        spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
