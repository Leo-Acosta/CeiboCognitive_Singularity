import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = {"instruction", "response"}


def normalize_record(record: dict) -> dict:
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
    return {
        "instruction": str(record["instruction"]).strip(),
        "input": str(record.get("input", "")).strip(),
        "response": str(record["response"]).strip(),
        "tags": list(record.get("tags", [])),
    }


def prepare_dataset(source: Path, target: Path) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with source.open("r", encoding="utf-8-sig") as input_file, target.open(
        "w", encoding="utf-8"
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                record = normalize_record(json.loads(line))
            except Exception as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and normalize CEIBO JSONL datasets.")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    count = prepare_dataset(args.source, args.target)
    print(f"Prepared {count} examples -> {args.target}")


if __name__ == "__main__":
    main()
