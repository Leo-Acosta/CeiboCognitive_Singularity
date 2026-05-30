# Seguridad

## Modelo base

CEIBO CORE debe operar con Zero Trust basico: ningun agente recibe privilegios
globales por defecto, y toda accion sensible pasa por politicas, auditoria y
limites de ejecucion.

## Controles iniciales

- JWT con issuer propio.
- OAuth2-ready para proveedores externos.
- RBAC por usuario, rol, agente y herramienta.
- RBAC v1 por headers `X-CEIBO-User` y `X-CEIBO-Role`.
- Roles iniciales: `admin`, `operator`, `researcher`, `viewer`.
- En desarrollo local, `LOCAL_DEV_ADMIN_ENABLED=true` permite admin implicito sin romper el flujo local.
- En produccion debe activarse `RBAC_ENFORCED=true` y desactivar admin implicito.
- Secret management mediante Kubernetes Secrets en desarrollo y External Secrets/Vault en produccion.
- Rate limiting en gateway.
- Auditoria centralizada para acciones de sistema, infraestructura y seguridad.
- Audit Trail v1 para registrar acciones sensibles permitidas y bloqueadas.
- Endpoint de consulta: `GET /api/v1/status/audit`.
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
