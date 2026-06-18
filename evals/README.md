# Evals

Dataset Pack v0.1 evalua Ceibo Core Conversational, Ceibo Legal Laboral y
Ceibo Ingenieria Inversa. Los casos comparan modelo base, base + prompt,
base + RAG, base + adaptador y base + adaptador + RAG.

Cada linea JSONL declara `id`, `vertical`, `input`, `expected_behavior`,
`must_include`, `must_avoid`, `risk_level` y `scoring_dimensions`.
