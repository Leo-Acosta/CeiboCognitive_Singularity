# Prompt operativo de Ceibo Cognitive Singularity

Este documento conserva la intencion estrategica del prompt fundador del
proyecto y la convierte en una directiva operativa para arquitectura,
implementacion y evolucion.

## Identidad

Ceibo Cognitive Singularity es un sistema local multiagente orientado a
inteligencia autonoma progresiva.

CEIBO CORE no debe ser tratado como un chatbot simple, sino como una
arquitectura viva de inteligencia artificial capaz de aprender, recordar,
razonar, actuar, coordinar agentes, entrenarse con datos propios, evaluar su
progreso y mejorar por ciclos controlados.

## Directiva principal

Construir una plataforma de inteligencia artificial local, modular, escalable,
entrenable, segura y multiagente, preparada para evolucionar desde asistente IA
local hacia sistema de inteligencia autonoma progresiva.

## Principio fundamental

La Singularidad no se afirma como logro presente. Se define como horizonte
tecnico medible. Todo avance debe expresarse en capacidades verificables,
metricas, evaluaciones, versionado, auditoria y control humano.

## Capacidades objetivo

- Aprendizaje continuo mediante datasets curados y feedback.
- Mejora progresiva de respuestas mediante evaluacion y fine-tuning.
- Coordinacion de agentes especializados por un Core Orchestrator.
- Uso de herramientas del sistema bajo politicas de seguridad.
- Memoria de largo plazo con RAG y base vectorial.
- Entrenamiento de modelos personalizados con LoRA/QLoRA.
- Analisis del propio rendimiento con evaluaciones repetibles.
- Automatizacion de tareas complejas con humano-en-el-bucle.
- Integracion con infraestructura real: Docker, Kubernetes, GPU y observabilidad.
- Expansion futura hacia voz, vision, robotica y sistemas distribuidos.

## Reglas de arquitectura

- Priorizar seguridad y control humano.
- Mantener arquitectura modular, local-first y preparada para Kubernetes.
- Preparar el sistema para modelos locales entrenables y GPU.
- Separar memoria, RAG, entrenamiento, agentes, herramientas y auditoria.
- Registrar acciones, decisiones y cambios de modelo.
- Evitar humo: toda mejora debe ser medible, reversible y documentada.

## Agentes base

- CORE Orchestrator.
- Memory Agent.
- Research Agent.
- Training Agent.
- Self-Improvement Agent.
- Infrastructure Agent.
- System Control Agent.
- Cybersecurity Agent.
- Voice Agent.
- Multimodal Agent.

## Ciclo de mejora

1. El usuario interactua con CEIBO.
2. CEIBO responde.
3. El sistema guarda la conversacion.
4. Usuario o Teacher IA evalua la respuesta.
5. Dataset Curator limpia y puntua ejemplos.
6. Training Agent prepara fine-tuning.
7. Se entrena un adapter QLoRA.
8. Se evalua el nuevo modelo.
9. Se compara contra el modelo anterior.
10. Si mejora, se registra como nueva version.
11. CEIBO usa la version promovida.
12. El ciclo vuelve a empezar.

## Resultado esperado

Una plataforma profesional, local, multiagente, entrenable y auto-mejorable,
cuyo progreso hacia inteligencia autonoma avanzada se mida con el Singularity
Index y con evaluaciones tecnicas reales.
