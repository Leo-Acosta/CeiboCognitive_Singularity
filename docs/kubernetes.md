# Kubernetes

## Namespaces

- `ceibo-core`: API, frontend y servicios de aplicacion.
- `ceibo-data`: bases de datos, cache, vector DB y bus de eventos.
- `ceibo-observability`: Prometheus, Grafana, Loki y collectors.

## Recursos generados

- Deployments: API, frontend, Redis, NATS.
- StatefulSets: PostgreSQL, Qdrant.
- ConfigMap: configuracion no sensible.
- Secret: claves JWT y proveedores IA.
- Services: exposicion interna.
- Ingress: Traefik/NGINX compatible.

## Comandos

```bash
kubectl apply -f infra/k8s/namespaces.yaml
helm upgrade --install ceibo-core charts/ceibo-core -n ceibo-core --create-namespace
```

## GPU futuro

Para vLLM/Ollama GPU se agregara:

- `nvidia.com/gpu` limits.
- `nodeSelector` para nodos GPU.
- `RuntimeClass` nvidia si aplica.
- HPA/KEDA segun cola de inferencia.
- Separacion de workloads IA pesados en namespace dedicado.
