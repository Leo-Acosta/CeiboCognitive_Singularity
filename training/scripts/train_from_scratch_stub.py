import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="CEIBO from-scratch training placeholder.")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print("CEIBO scratch pretraining plan loaded.")
    print(f"Model: {config['model_name']}")
    print(f"Dataset: {config['dataset']}")
    print(f"Output: {config['output_model']}")
    print("This is a research path. Use it for small controlled models, not foundation-scale training.")


if __name__ == "__main__":
    main()
