from __future__ import annotations

import json
from pathlib import Path

from ceibo_core.core.product_router import route_product_query


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_product_router_preserves_human_dialogue_for_legal_mode():
    route = route_product_query("Necesito revisar una clausula laboral de un contrato")

    assert route["mode"] == "legal"
    assert route["rag_namespace"] == "ceibo_legal"
    assert route["human_interaction"]["preserve_natural_dialogue"] is True
    assert route["human_interaction"]["ask_clarifying_questions"] is True


def test_training_configs_are_valid_json_and_reference_datasets():
    configs = sorted((REPO_ROOT / "training" / "configs").glob("ceibo_*_lora.json"))
    configs += [REPO_ROOT / "training" / "configs" / "ceibo_core_qwen3b_smoke.json"]

    assert configs
    for config_path in configs:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["base_model"]
        assert data["dataset_path"].startswith("training/datasets/")
        assert data["load_in_4bit"] is True
        assert data["target_modules"]


def test_seed_datasets_are_valid_jsonl_and_es_ar():
    dataset_roots = sorted((REPO_ROOT / "training" / "datasets").glob("ceibo_*"))

    assert dataset_roots
    for dataset_root in dataset_roots:
        seed_path = dataset_root / "seed.jsonl"
        if not seed_path.exists():
            continue
        rows = [json.loads(line) for line in seed_path.read_text(encoding="utf-8").splitlines()]
        assert rows
        for row in rows:
            assert set(["instruction", "input", "response", "tags", "metadata"]).issubset(row)
            assert row["metadata"]["language"] == "es-AR"


def test_model_registry_example_has_planned_adapters():
    registry_path = REPO_ROOT / "models" / "registry" / "model_registry.example.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    ids = {entry["id"] for entry in registry["entries"]}
    assert "ceibo-core-qwen7b-lora-v0.1" in ids
    assert "ceibo-code-qwen-coder7b-lora-v0.1" in ids
