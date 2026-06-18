from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ROOT / "training/datasets/ceibo_core/curated.jsonl",
    ROOT / "training/datasets/ceibo_legal/curated.jsonl",
    ROOT / "training/datasets/ceibo_reverse_engineering/curated.jsonl",
]
OUTPUT = ROOT / "training/datasets/combined/ceibo_dataset_pack_v0.1.curated.jsonl"
REQUIRED = {"instruction", "input", "response", "tags", "source", "rating", "metadata"}


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} invalid JSONL: {exc}") from exc
        missing = REQUIRED - row.keys()
        if missing:
            raise ValueError(f"{path}:{line_number} missing fields: {sorted(missing)}")
        if row.get("rating", 0) < 4 or "bad_example" in row.get("tags", []):
            raise ValueError(f"{path}:{line_number} curated dataset contains a bad/low-rating example")
        row.setdefault("metadata", {})
        row["metadata"]["combined_dataset_pack"] = "v0.1"
        rows.append(row)
    return rows


def main() -> None:
    combined: list[dict] = []
    for source in SOURCES:
        if not source.exists():
            raise FileNotFoundError(source)
        combined.extend(read_jsonl(source))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in combined) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(combined)} examples to {OUTPUT}")


if __name__ == "__main__":
    main()
