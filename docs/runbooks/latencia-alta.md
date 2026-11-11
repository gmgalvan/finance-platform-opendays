# Runbook: LatenciaAlta

| | |
|---|---|
| **Alerta** | `LatenciaAlta` (severidad `ticket`) |
| **Significa** | Menos del 95 % de las solicitudes responde en menos de 500 ms. |
| **Impacto** | La app funciona, pero se siente lenta. No requiere despertar a nadie: se atiende en horario laboral. |

Si también está activa `AltaTasaDeErrores`, Alertmanager suprime esta alerta: atender primero [AltaTasaDeErrores](alta-tasa-de-errores.md).

## 1. ¿Qué endpoint es lento?

Grafana → panel **Latencia (p50 y p95)**, o en Prometheus:

```promql
histogram_quantile(0.95, sum by (le, path) (rate(finance_api_request_duration_seconds_bucket{path!~"/metrics|/health"}[5m])))
```

## 2. ¿Dónde se va el tiempo?

Jaeger (http://localhost:16686): elegir el servicio y la operación del endpoint lento, **Min Duration** = `500ms`, y abrir una traza.

| Span que domina | Probable causa |
|---|---|
| `consultar_proveedor` (market-data) | Proveedor externo lento |
| `hash_password` | Más suscripciones que de costumbre (PBKDF2 es lento a propósito) |
| `INSERT` / `SELECT` | PostgreSQL saturado |

## 3. ¿Hay suficiente capacidad?

```bash
kubectl -n finance top pods 2>/dev/null || kubectl -n finance get pods
```

Escalar temporalmente el servicio afectado:

```bash
kubectl -n finance scale deployment/api --replicas=3
```

## 4. Cerrar

Registrar la causa y, si se escaló a mano, decidir si el cambio debe quedar en `deploy/kubernetes/`.
