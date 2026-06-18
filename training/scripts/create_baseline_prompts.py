from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_FILES = [
    PROJECT_ROOT / "evals/ceibo_core_eval.jsonl",
    PROJECT_ROOT / "evals/ceibo_legal_eval.jsonl",
    PROJECT_ROOT / "evals/ceibo_reverse_engineering_eval.jsonl",
]
OUTPUT = PROJECT_ROOT / "evals/baseline_prompts_qwen3b_smoke.md"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def select_cases() -> list[dict]:
    selected: list[dict] = []
    for path in EVAL_FILES:
        rows = read_jsonl(path)
        selected.extend(rows[:4])
    return selected[:10]


def render_prompt(case: dict, index: int) -> str:
    return f"""## Prompt {index}: {case["id"]}

- Vertical: `{case["vertical"]}`
- Input: {case["input"]}
- Expected behavior: {case["expected_behavior"]}
- Must include: {", ".join(case["must_include"])}
- Must avoid: {", ".join(case["must_avoid"])}
- Scoring dimensions: {", ".join(case["scoring_dimensions"])}

### Manual Test Prompt

```text
Sos Ceibo Core, el cerebro conversacional, cognitivo y agente de Ceibo AI.
Respondé en español argentino profesional, con naturalidad, seguridad y claridad.

Usuario:
{case["input"]}
```

Probar con:

- Qwen base.
- Qwen + prompt Ceibo.
- Qwen + adaptador smoke cuando exista.
"""


def main() -> None:
    cases = select_cases()
    content = [
        "# Baseline Prompts Qwen 3B Smoke",
        "",
        "Prompts manuales para comparar Qwen base, Qwen + prompt Ceibo y Qwen + adaptador smoke.",
        "No llama APIs externas, no descarga modelos y no entrena.",
        "",
    ]
    for index, case in enumerate(cases, start=1):
        content.append(render_prompt(case, index))
    OUTPUT.write_text("\n".join(content).strip() + "\n", encoding="utf-8")
    print(f"Wrote {len(cases)} prompts to {OUTPUT}")


if __name__ == "__main__":
    main()
