# Seguridad

## Modelo base

CEIBO CORE debe operar con Zero Trust basico: ningun agente recibe privilegios
globales por defecto, y toda accion sensible pasa por politicas, auditoria y
limites de ejecucion.

## Controles iniciales

- JWT con issuer propio.
- OAuth2-ready para proveedores externos.
- RBAC por usuario, rol, agente y herramienta.
- Secret management mediante Kubernetes Secrets en desarrollo y External Secrets/Vault en produccion.
- Rate limiting en gateway.
- Auditoria centralizada para acciones de sistema, infraestructura y seguridad.
- Sandboxing para terminal, archivos y automatizacion desktop.
- Logs estructurados JSON.
- TLS en Ingress.

## Zonas de riesgo

- Control de terminal.
- Escritura de archivos.
- Automatizacion de navegador con sesiones autenticadas.
- Acceso a Kubernetes y Docker socket.
- Lectura de secretos.
- Ejecucion de scripts generados por IA.

Estas capacidades deben comenzar deshabilitadas y activarse por politica.
