# Ceibo AI Training Lifecycle

1. Recoleccion de ejemplos.
2. Limpieza.
3. Anonimizacion.
4. Curacion.
5. Validacion.
6. Fine-tuning QLoRA.
7. Evaluacion.
8. Comparacion con baseline.
9. Registro de version.
10. Publicacion de adaptador.
11. Monitoreo.
12. Reentrenamiento.
13. Evaluacion de la capacidad conversacional humana de Ceibo Core.
14. Evaluacion de capacidad para operar verticales sin perder dialogo natural.

Qwen 3B sirve para smoke tests; Qwen 7B como base general inicial; Qwen Coder
7B para Ceibo Code; Mistral queda como alternativa. Ollama sirve para
ejecucion local/demo. QLoRA requiere modelos compatibles con
HuggingFace/Transformers y no directamente GGUF/Ollama.

## Dataset Pack v0.1

El primer ciclo de datos entrenables usa ejemplos sinteticos controlados,
seguros y revisables para Ceibo Core Conversational, Legal Laboral y Reverse
Engineering. Antes de entrenar se valida JSONL, se separan bad examples, se
ejecutan evals y se corre un Qwen 3B smoke test de bajo costo.
