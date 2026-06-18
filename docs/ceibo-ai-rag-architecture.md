# Ceibo AI RAG Architecture

RAG usa documentos curados por vertical: leyes, jurisprudencia validada,
plantillas, manuales, KB tecnica, reportes anonimizados y guias internas. Los
documentos se chunkearan por estructura semantica, version, fuente y riesgo.

Qdrant o pgvector almacenan embeddings separados por namespace: ceibo_core,
ceibo_legal, ceibo_empleo, ceibo_forense, ceibo_code, ceibo_economics y
ceibo_agents. Ceibo Core consulta RAG sin perder dialogo natural: primero
entiende la conversacion, luego recupera evidencia, cita fuentes y responde
con claridad.

Si no hay base documental suficiente, Ceibo Core debe decirlo, pedir fuentes o
responder como orientacion general. Cada respuesta RAG debe registrar consulta,
namespace, chunks, version, fuentes y decision de guardrails.
