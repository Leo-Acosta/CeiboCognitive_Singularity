import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from ceibo_core.models.schemas import DatasetCurationRequest  # noqa: E402
from ceibo_core.services.dataset_curator import DatasetCuratorService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate, score, deduplicate and export a curated CEIBO JSONL dataset."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default="training/datasets/ceibo_instructions.jsonl",
        help="Source JSONL path inside the project.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL path. Defaults to source filename with .curated.jsonl suffix.",
    )
    parser.add_argument("--min-score", type=int, default=60, help="Minimum quality score.")
    parser.add_argument(
        "--include-bad-rated",
        action="store_true",
        help="Keep examples explicitly rated as bad if they pass score checks.",
    )
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Analyze and print a report without writing the curated file.",
    )
    args = parser.parse_args()

    service = DatasetCuratorService()
    try:
        report = service.curate(
            DatasetCurationRequest(
                source_path=args.source,
                output_path=args.output,
                min_score=args.min_score,
                include_bad_rated=args.include_bad_rated,
                max_examples=args.max_examples,
            ),
            write_output=not args.preview_only,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    summary = {
        "source_path": report.source_path,
        "output_path": report.output_path,
        "parsed_examples": report.parsed_examples,
        "kept_examples": report.kept_examples,
        "dropped_examples": report.dropped_examples,
        "invalid_lines": report.invalid_lines,
        "duplicate_examples": report.duplicate_examples,
        "average_score": report.average_score,
        "score_buckets": report.score_buckets,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if report.issues:
        print("\nTop issues:")
        for issue in report.issues[:10]:
            location = f"line {issue.line_number}" if issue.line_number else "dataset"
            print(f"- [{issue.severity}] {issue.code} at {location}: {issue.message}")


if __name__ == "__main__":
    main()
