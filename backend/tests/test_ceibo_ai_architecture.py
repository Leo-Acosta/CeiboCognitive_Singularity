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


def test_product_router_recognizes_reverse_engineering_mode():
    route = route_product_query(
        "Necesito ingenieria inversa autorizada para documentar arquitectura legacy"
    )

    assert route["mode"] == "reverse_engineering"
    assert route["agent"] == "architecture_analysis_agent"
    assert route["rag_namespace"] == "ceibo_reverse_engineering"
    assert route["adapter"] == "ceibo_reverse_engineering_qwen7b_lora"
    assert "authorized_analysis_only" in route["guardrails"]
    assert "clean_room_spec_generator" in route["tools"]
    assert route["human_interaction"]["preserve_natural_dialogue"] is True


def test_product_router_recognizes_academic_writing_mode():
    route = route_product_query("Necesito armar una tesis doctoral con metodologia y APA 7")

    assert route["mode"] == "academic_writing"
    assert route["agent"] == "thesis_planner_agent"
    assert route["rag_namespace"] == "ceibo_academic_writing"
    assert route["adapter"] == "ceibo_academic_writing_qwen7b_lora"
    assert "academic_integrity_required" in route["guardrails"]
    assert "no_fake_sources" in route["guardrails"]
    assert "thesis_outline_generator" in route["tools"]
    assert route["human_interaction"]["preserve_natural_dialogue"] is True


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
    assert "ceibo-reverse-engineering-qwen7b-lora-v0.1" in ids
    assert "ceibo-academic-writing-qwen7b-lora-v0.1" in ids


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_dataset_pack_v0_1_minimum_counts_and_metadata():
    expectations = {
        "ceibo_core": (25, 8, 12),
        "ceibo_legal": (30, 10, 15),
        "ceibo_reverse_engineering": (25, 10, 12),
        "ceibo_academic_writing": (25, 10, 12),
    }

    for vertical, (min_good, min_bad, min_eval) in expectations.items():
        root = REPO_ROOT / "training" / "datasets" / vertical
        seed = _read_jsonl(root / "seed.jsonl")
        curated = _read_jsonl(root / "curated.jsonl")
        bad = _read_jsonl(root / "bad_examples.jsonl")
        eval_cases = _read_jsonl(root / "eval_cases.jsonl")

        assert len(seed) >= min_good
        assert len(curated) >= min_good
        assert len(bad) >= min_bad
        assert len(eval_cases) >= min_eval
        assert all(row["source"] == "synthetic_v0.1" for row in curated)
        assert all(row["metadata"]["dataset_pack"] == "v0.1" for row in curated)
        assert all("bad_example" not in row["tags"] for row in curated)
        assert all(row["rating"] >= 4 for row in curated)


def test_ceibo_core_dataset_preserves_natural_dialogue():
    rows = _read_jsonl(REPO_ROOT / "training" / "datasets" / "ceibo_core" / "curated.jsonl")

    assert rows
    assert all(row["metadata"]["preserve_natural_dialogue"] is True for row in rows)


def test_dataset_pack_eval_schema_and_dimensions():
    eval_files = [
        REPO_ROOT / "evals" / "ceibo_core_eval.jsonl",
        REPO_ROOT / "evals" / "ceibo_legal_eval.jsonl",
        REPO_ROOT / "evals" / "ceibo_reverse_engineering_eval.jsonl",
    ]

    for eval_file in eval_files:
        rows = _read_jsonl(eval_file)
        assert rows
        for row in rows:
            assert {"id", "vertical", "input", "expected_behavior", "must_include", "must_avoid"}.issubset(row)
            assert row["scoring_dimensions"]

    legal_rows = _read_jsonl(REPO_ROOT / "evals" / "ceibo_legal_eval.jsonl")
    assert all("human_review_required" in row["scoring_dimensions"] for row in legal_rows)
    reverse_rows = _read_jsonl(REPO_ROOT / "evals" / "ceibo_reverse_engineering_eval.jsonl")
    assert all("authorization_check" in row["scoring_dimensions"] for row in reverse_rows)
    academic_rows = _read_jsonl(REPO_ROOT / "evals" / "ceibo_academic_writing_eval.jsonl")
    assert all("academic_integrity" in row["scoring_dimensions"] for row in academic_rows)


def test_academic_writing_config_and_dataset_guardrails():
    config = json.loads(
        (
            REPO_ROOT
            / "training"
            / "configs"
            / "ceibo_academic_writing_qwen7b_lora.json"
        ).read_text(encoding="utf-8")
    )
    rows = _read_jsonl(
        REPO_ROOT / "training" / "datasets" / "ceibo_academic_writing" / "curated.jsonl"
    )
    bad_rows = _read_jsonl(
        REPO_ROOT / "training" / "datasets" / "ceibo_academic_writing" / "bad_examples.jsonl"
    )

    assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert config["dataset_path"] == "training/datasets/ceibo_academic_writing/curated.jsonl"
    assert config["preserve_natural_dialogue"] is True
    assert config["academic_integrity_required"] is True
    assert rows and bad_rows
    assert all(row["metadata"]["academic_integrity_required"] is True for row in rows)
    assert all(row["metadata"]["human_author_required"] is True for row in rows)
    assert all("bad_example" not in row["tags"] for row in rows)
    assert all("bad_example" in row["tags"] for row in bad_rows)


def test_qwen3b_smoke_config_is_fast_and_non_production():
    config = json.loads(
        (REPO_ROOT / "training" / "configs" / "ceibo_core_qwen3b_smoke.json").read_text(
            encoding="utf-8"
        )
    )

    assert config["base_model"] == "Qwen/Qwen2.5-3B-Instruct"
    assert config["dataset_path"] == "training/datasets/combined/ceibo_dataset_pack_v0.1.curated.jsonl"
    assert config["output_dir"] == "models/adapters/ceibo-core-conversational-qwen3b-smoke-v0.1"
    assert config["lora_r"] == 8
    assert config["lora_alpha"] == 16
    assert config["gradient_accumulation_steps"] == 4
    assert config["max_steps"] <= 5
    assert config["load_in_4bit"] is True
    assert "Not production quality" in config["notes"]


def test_combined_dataset_pack_contains_only_curated_positive_examples():
    combined = _read_jsonl(
        REPO_ROOT
        / "training"
        / "datasets"
        / "combined"
        / "ceibo_dataset_pack_v0.1.curated.jsonl"
    )

    assert len(combined) >= 80
    assert all(row["rating"] >= 4 for row in combined)
    assert all("bad_example" not in row["tags"] for row in combined)
    assert {row["metadata"]["vertical"] for row in combined} == {
        "ceibo_core",
        "ceibo_legal",
        "ceibo_reverse_engineering",
    }
