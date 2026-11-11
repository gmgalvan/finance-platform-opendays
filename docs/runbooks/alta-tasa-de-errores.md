# Runbook: AltaTasaDeErrores

| | |
|---|---|
| **Alerta** | `AltaTasaDeErrores` (severidad `page`) |
| **Significa** | Más del 5 % de las solicitudes de usuarios a la API terminan en error 5xx. El presupuesto de error del SLO de 99 % se está gastando más de 5 veces más rápido de lo permitido. |
| **Impacto** | Parte de los usuarios ve errores. Si dura, se agota el presupuesto de error. |
| **Objetivo** | **Mitigar primero** (detener el daño); investigar la causa raíz después. |

## 1. Confirmar la alerta (1 min)

```bash
make alerts
```

- Alertmanager: http://localhost:9093
- Grafana, fila **SLO**: http://localhost:3000. Revisar **Velocidad de consumo** y **Disponibilidad vs SLO**.

Si la velocidad de consumo ya bajó de 5, la alerta se resolverá sola: vigilar y documentar.

## 2. ¿Qué endpoint falla? (1 min)

En Grafana, panel **Respuestas por código HTTP** y **Solicitudes por segundo, por endpoint**.

O en Prometheus (http://localhost:9090):

```promql
sum by (path, status) (rate(finance_api_requests_total{status=~"5.."}[5m]))
```

| Si falla... | Probable origen | Seguir en |
|---|---|---|
| `/api/market/quotes` (503) | El servicio **market-data** | Paso 3 |
| `/api/subscriptions` o `/api/dashboard` (503) | **PostgreSQL** | Paso 5 |
| Todos los endpoints (500) | La **API** misma | Paso 4 |

## 3. Origen en market-data

**Jaeger** (http://localhost:16686): Service `market-data` → Tags `error=true` → Find Traces. Una traza con error muestra en rojo el span que falló y el mensaje.

**Logs y estado:**

```bash
kubectl -n finance get pods -l app.kubernetes.io/name=market-data
kubectl -n finance logs -l app.kubernetes.io/name=market-data --tail=30 --prefix
```

**¿Qué cambió recientemente?** La mayoría de los incidentes empiezan con un cambio.

```bash
kubectl -n finance rollout history deployment/market-data
kubectl -n finance get deployment market-data -o jsonpath='{.spec.template.spec.containers[0].env}'; echo
```

### Mitigar: rollback a la revisión anterior

```bash
kubectl -n finance rollout undo deployment/market-data
kubectl -n finance rollout status deployment/market-data
```

(En la demo: `make demo-recover`.)

## 4. Origen en la API

```bash
kubectl -n finance rollout history deployment/api
kubectl -n finance logs -l app.kubernetes.io/name=api --tail=50 --prefix
```

Si coincide con un despliegue reciente: `kubectl -n finance rollout undo deployment/api` (o `make k8s-rollback` para todos los servicios).

## 5. Origen en PostgreSQL

```bash
kubectl -n finance get pod postgres-0
kubectl -n finance logs postgres-0 --tail=50
curl -s localhost:8090/api/health
```

Si `/api/health` responde `La base de datos no está disponible`, revisar eventos con `kubectl -n finance describe pod postgres-0`.

## 6. Verificar la recuperación (2-3 min)

- **Respuestas por código HTTP**: los 5xx bajan a 0.
- **Velocidad de consumo (5 m)**: baja de 5.
- `make alerts` → `Sin alertas activas`.

## 7. Cerrar

1. Avisar que el servicio se recuperó.
2. Registrar la hora de inicio, detección y recuperación.
3. Programar la retrospectiva con [la plantilla](retrospectiva-plantilla.md).
