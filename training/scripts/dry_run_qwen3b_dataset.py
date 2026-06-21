from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from preflight_qwen3b_smoke import DEFAULT_CONFIG, resolve_project_path


SYSTEM_PROMPT = (
    "Sos Ceibo Core, el cerebro conversacional, cognitivo y agente de Ceibo AI. "
    "Respondés en español argentino profesional, con naturalidad, seguridad y claridad."
)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(resolve_project_path(path).read_text(encoding="utf-8"))


def read_examples(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def fallback_qwen_format(example: dict[str, Any]) -> str:
    input_text = str(example.get("input") or "").strip()
    user = f"Instruction: {example['instruction']}"
    if input_text:
        user += f"\nInput: {input_text}"
    return (
        "<|im_start|>system\n"
        f"{SYSTEM_PROMPT}\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"{user}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{example['response']}\n"
        "<|im_end|>"
    )


def generic_format(example: dict[str, Any]) -> str:
    return (
        f"Instruction: {example['instruction']}\n"
        f"Input: {example.get('input', '')}\n"
        f"Response: {example['response']}"
    )


def try_local_chat_template(example: dict[str, Any], base_model: str) -> str | None:
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            base_model,
            local_files_only=True,
            trust_remote_code=True,
        )
    except Exception:
        return None

    if not getattr(tokenizer, "chat_template", None):
        return None

    input_text = str(example.get("input") or "").strip()
    content = f"Instruction: {example['instruction']}"
    if input_text:
        content += f"\nInput: {input_text}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
        {"role": "assistant", "content": str(example["response"])},
    ]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False)
    except Exception:
        return None


def format_example(example: dict[str, Any], base_model: str) -> tuple[str, str]:
    templated = try_local_chat_template(example, base_model)
    if templated:
        return "tokenizer_chat_template_local", templated
    if "qwen" in base_model.casefold():
        return "fallback_qwen", fallback_qwen_format(example)
    return "generic", generic_format(example)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run Dataset Pack v0.1 formatting.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    dataset_path = resolve_project_path(config.get("dataset_path") or config.get("dataset"))
    examples = read_examples(dataset_path, max(1, args.limit))

    print("Qwen 3B Dataset Dry Run")
    print("=" * 25)
    print(f"Dataset: {dataset_path}")
    print(f"Ejemplos mostrados: {len(examples)}")
    print("No se descarga modelo, no se entrena, no se requiere GPU.")
    for index, example in enumerate(examples, start=1):
        formatter, text = format_example(example, str(config["base_model"]))
        print("\n" + "-" * 80)
        print(f"Example {index} | formatter={formatter} | vertical={example.get('metadata', {}).get('vertical')}")
        print(text[:3000])

    print("\nResultado: formato compatible con instruction tuning si instruction/response son claros.")


if __name__ == "__main__":
    main()
