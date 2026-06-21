# Combined Dataset Pack v0.1

`training/scripts/build_dataset_pack_v0_1.py` combina los `curated.jsonl` de
Ceibo Core, Ceibo Legal Laboral y Ceibo Reverse Engineering en:

`training/datasets/combined/ceibo_dataset_pack_v0.1.curated.jsonl`

El archivo combinado es pequeno y puede generarse para smoke tests. Validar que
no contenga bad examples ni datos sensibles antes de entrenar.
