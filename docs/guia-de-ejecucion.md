# Guía de ejecución

Bitácora paso a paso de lo que se ha construido para la demo: qué se hizo, qué comandos ejecutar y qué resultado esperar. Sirve para repetir cada etapa y para ensayar la charla.

Repositorio: https://github.com/gmgalvan/finance-platform-opendays

## Preparación de la máquina

| Herramienta | Para qué | Comprobar |
|---|---|---|
| Git | Control de versiones | `git --version` |
| GitHub CLI | Abrir PRs y revisar el CI desde la terminal | `gh auth status` |
| uv | Crear el entorno de Python 3.12 para las pruebas | `uv --version` |
| Docker Desktop | Levantar la app, PostgreSQL de pruebas y Kind | `docker ps` |
| kind | Crear el clúster local de Kubernetes | `kind version` |
| kubectl | Operar el clúster | `kubectl version --client` |
| Terraform | Validar la infraestructura | `terraform version` |
| Node.js | Revisar la sintaxis del JavaScript | `node --version` |

### Cuenta de GitHub

La cuenta activa de `gh` debe ser **gmgalvan** y necesita el permiso `workflow` para subir cambios en `.github/workflows/`:

```bash
gh auth status                              # cuenta activa y permisos
gh auth switch --user gmgalvan              # si la activa es otra
gh auth refresh -h github.com -s workflow   # agregar el permiso workflow
gh auth setup-git                           # usar gh para git push por HTTPS
```

Sin el permiso `workflow`, el push falla con `refusing to allow an OAuth App to create or update workflow`.

---

## Paso 0 — Crear el repositorio y el primer commit

1. Se creó el repositorio público vacío `gmgalvan/finance-platform-opendays` desde GitHub.
2. Se agregó un `.gitignore` en la raíz para no subir:
   - estado y planes de Terraform (`*.tfstate`, `*.tfplan`, `.terraform/`);
   - paquetes generados (`build/`);
   - secretos (`.env`, `*.pem`, `*.key`);
   - entornos de Python (`.venv/`).
3. Primer commit y push:

```bash
git init -b main
git add -A
git status --short          # revisar que no aparezca nada sensible
git commit -m "Initial commit"
git remote add origin https://github.com/gmgalvan/finance-platform-opendays.git
git push -u origin main
```

---

## Paso 1 — Pruebas locales (Stage 5A)

Las pruebas viven en `tests/`:

| Carpeta | Qué revisa |
|---|---|
| `tests/api/` | Validaciones, contraseñas, `/health`, `/metrics` y suscripciones contra PostgreSQL |
| `tests/frontend/` | Enlaces rotos, anclas, idioma, título y sintaxis JavaScript |
| `tests/infrastructure/` | Reglas de seguridad de Terraform: sin SSH, IMDSv2, cifrado, bucket privado |
| `tests/smoke/smoke.sh` | Recorrido completo contra la app en ejecución |

Ejecutarlas:

```bash
make test-setup     # una sola vez: crea .venv con Python 3.12
make test-db-up     # PostgreSQL de pruebas (requiere Docker)
make test           # pytest + terraform fmt + terraform validate
make test-db-down
```

**Resultado esperado:** 29 pruebas en verde. Sin Docker, las 5 pruebas de base de datos aparecen como `skipped` y el resto pasa.

Smoke test contra la app completa:

```bash
make stage-2-up
make smoke
make stage-2-down
```

---

## Paso 2 — CI en Pull Requests

Archivo: `.github/workflows/pull-request.yml`. Corre en cada PR hacia `main` y en cada push a `main`.

| Job | Qué hace | Tiempo aprox. |
|---|---|---:|
| Frontend | Pruebas de `tests/frontend` | 20 s |
| API + PostgreSQL | Pruebas de `tests/api` con una base de datos real | 30 s |
| Terraform | `fmt`, `validate` y reglas de seguridad | 20 s |
| Seguridad | gitleaks, pip-audit y dependency review | 20 s |
| Docker + smoke test | Construye las imágenes, levanta la app y ejecuta `smoke.sh` | 45 s |
| CI passed | Resume todo: verde solo si todos pasaron | 3 s |
| Kubernetes | Genera los manifiestos, los valida con kubeconform y exige imágenes con `sha-<commit>` | 15 s |
| Publicar imágenes | Solo en `main`: publica las imágenes en GHCR (ver Paso 5) | 1 min |

Flujo para cualquier cambio:

```bash
git checkout main && git pull
git checkout -b mi-cambio
# ... editar archivos ...
git add -A && git commit -m "Describe el cambio"
git push -u origin mi-cambio
gh pr create --fill
gh pr checks --watch        # ver el CI en vivo desde la terminal
gh pr merge --squash --delete-branch
git checkout main && git pull
```

Configuración adicional en GitHub:

- **Dependabot alerts** activadas. Encienden el *Dependency graph* que necesita dependency review.

---

## Paso 3 — Proteger `main`

Se configuró con la API de GitHub (equivale a *Settings → Branches*):

- El check **CI passed** es obligatorio y la rama debe estar actualizada.
- La regla aplica también al administrador.
- No se permite force push ni borrar `main`.
- Las conversaciones del PR deben estar resueltas.

Comprobar la configuración:

```bash
gh api repos/gmgalvan/finance-platform-opendays/branches/main/protection \
  --jq '{checks: [.required_status_checks.checks[].context], admins: .enforce_admins.enabled}'
```

---

## Paso 4 — Ensayo: un PR que el CI bloquea

Demo para la charla: alguien abre SSH "para depurar".

```bash
git checkout -b demo/abrir-ssh
```

Agregar en `infra/terraform/aws-ec2/main.tf`, dentro de `aws_security_group.web`:

```hcl
  ingress {
    description = "SSH temporal para depurar"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
```

```bash
git commit -am "Demo: abrir SSH para depurar"
git push -u origin demo/abrir-ssh
gh pr create --fill
gh pr checks --watch
```

**Resultado esperado:**

- `terraform fmt` y `terraform validate` pasan: el código es válido.
- La política `test_ssh_port_is_not_open` falla con `assert 22 not in {0, 22, 80}`.
- **CI passed** queda en rojo y GitHub muestra *Merging is blocked*.
- `gh pr merge` responde `the base branch policy prohibits the merge`.

Limpiar sin tocar `main`:

```bash
gh pr close --delete-branch
git checkout main
git branch -D demo/abrir-ssh
```

Ejemplo real: PR #2 del repositorio.

---

## Paso 5 — Publicar imágenes en GHCR (Stage 5B)

Al hacer merge en `main`, si **CI passed** está en verde, el job **Publicar imágenes** construye y publica:

- `ghcr.io/gmgalvan/finance-platform-api`
- `ghcr.io/gmgalvan/finance-platform-frontend`

Cada imagen recibe dos etiquetas:

| Etiqueta | Significado |
|---|---|
| `sha-<commit>` | Versión exacta: liga la imagen con el commit que la produjo |
| `latest` | La versión más reciente de `main` |

En un PR el job aparece como *skipped*: solo se publica lo que ya pasó el CI y llegó a `main`.

Comprobar las imágenes publicadas:

```bash
git rev-parse --short HEAD                                        # SHA del último commit
docker pull ghcr.io/gmgalvan/finance-platform-api:sha-<commit>
docker pull ghcr.io/gmgalvan/finance-platform-frontend:sha-<commit>
```

También se pueden ver en https://github.com/gmgalvan?tab=packages.

**Mensaje para la charla:** la imagen que se despliega es exactamente la que pasó las pruebas; no se vuelve a construir para cada ambiente.

---

## Paso 6 — Kubernetes con Kind (Stage 6)

**Idea:** Docker Compose ejecuta contenedores; Kubernetes mantiene un **estado deseado**. Si declaras 2 réplicas de la API, Kubernetes se asegura de que siempre existan 2.

Archivos:

| Archivo | Recursos | Para qué |
|---|---|---|
| `deploy/kind/cluster.yaml` | Clúster `finance` | Un nodo; publica el NodePort 30080 en `localhost:8090` |
| `deploy/kubernetes/namespace.yaml` | Namespace `finance` | Aísla los recursos de la app |
| `deploy/kubernetes/postgres.yaml` | Secret, Service, StatefulSet | PostgreSQL con disco persistente de 1 Gi |
| `deploy/kubernetes/api.yaml` | Service, Deployment (2 réplicas) | API con readiness en `/health` y liveness por TCP |
| `deploy/kubernetes/frontend.yaml` | Service NodePort, Deployment (2 réplicas) | Nginx y la página web |
| `deploy/kubernetes/kustomization.yaml` | Kustomize | Versión desplegada (`sha-<commit>`) y `init.sql` como ConfigMap |

### Levantar todo

Docker Desktop debe estar encendido.

```bash
make kind-up        # crea el clúster (≈ 30 s)
make k8s-deploy     # aplica los manifiestos y espera a que todo esté listo (≈ 1 min)
make k8s-status     # pods, servicios y versiones
make k8s-smoke      # smoke test contra http://localhost:8090
```

Abrir http://localhost:8090 en el navegador.

**Resultado esperado de `make k8s-status`:** 5 pods en `Running` (2 de API, 2 de frontend y `postgres-0`), y las imágenes con la etiqueta `sha-<commit>`.

### Demo: autorecuperación

En una terminal, observar los pods:

```bash
kubectl -n finance get pods -w
```

En otra, copiar el nombre de un pod de la API de esa lista y borrarlo:

```bash
kubectl -n finance delete pod <nombre-del-pod>
```

**Resultado esperado:** en 1 o 2 segundos aparece un pod nuevo con otro nombre. La app no deja de responder porque la segunda réplica atiende mientras tanto:

```bash
curl localhost:8090/api/health
```

**Mensaje para la charla:** nadie reinició nada a mano. Kubernetes compara el estado actual (1 réplica) con el deseado (2) y lo corrige.

### Readiness y liveness

- **Readiness** (`/health`): el pod recibe tráfico solo si la API llega a PostgreSQL.
- **Liveness** (TCP): Kubernetes reinicia el contenedor solo si el proceso deja de responder. No depende de la base de datos, para no reiniciar la API cuando la falla está en PostgreSQL.

### Comandos útiles

```bash
kubectl -n finance logs deployment/api            # logs de una réplica de la API
kubectl -n finance logs -l app.kubernetes.io/name=api --prefix
kubectl -n finance describe pod <nombre>          # eventos: descarga de imagen, probes, reinicios
kubectl -n finance exec -it postgres-0 -- psql -U finance -d finance_platform -c "SELECT email FROM users;"
make k8s-render                                   # ver el YAML final que se aplica
```

### Apagar

```bash
make kind-down      # borra el clúster y sus datos
```

---

## Paso 7 — Del PR a Kubernetes con Rolling Update (demo central)

**Idea:** un cambio recorre todo el camino: código → PR → CI → imagen versionada → Kubernetes, sin que la app deje de responder.

GitHub no puede entrar a Kind porque vive en la laptop. Por eso el CI **publica** la imagen y el último paso, **desplegar**, se ejecuta localmente con `make k8s-release`.

### Comandos

| Comando | Qué hace |
|---|---|
| `make k8s-release` | Toma el último commit de `main`, espera su imagen en GHCR y hace Rolling Update de API y frontend |
| `make k8s-release TAG=sha-<commit>` | Despliega una versión específica |
| `make k8s-watch` | Muestra los pods en vivo (dejar abierto en una terminal) |
| `make k8s-ping` | Consulta `/api/health` cada medio segundo (para demostrar que no hay caída) |
| `make k8s-history` | Historial de versiones desplegadas |
| `make k8s-rollback` | Regresa a la versión anterior |

### Preparar la pantalla

Tres terminales y el navegador:

1. **Terminal 1:** `make k8s-watch`
2. **Terminal 2:** `make k8s-ping`
3. **Terminal 3:** comandos de Git y `make k8s-release`
4. **Navegador:** http://localhost:8090

### Guion

```bash
# 1. Rama y cambio visible
git checkout main && git pull
git checkout -b demo/cambio-visible
# ... editar app/stage-2/frontend/index.html (o pedirlo a Claude Code) ...

# 2. Pull Request y CI
git add -A && git commit -m "Cambio visible en el dashboard"
git push -u origin demo/cambio-visible
gh pr create --fill
gh pr checks --watch           # ≈ 1 min

# 3. Merge: el CI corre en main y publica la imagen sha-<commit>
gh pr merge --squash --delete-branch
git checkout main && git pull

# 4. Desplegar en Kubernetes
make k8s-release               # espera la imagen (≈ 1-2 min tras el merge) y despliega
```

Recargar el navegador: aparece el cambio.

### Resultado esperado

`make k8s-release` muestra la versión anterior y la nueva:

```
Versión a desplegar: sha-123a90d
Esperando la imagen finance-platform-api:sha-123a90d en GHCR....... ✓
Esperando la imagen finance-platform-frontend:sha-123a90d en GHCR ✓
...
Waiting for deployment "api" rollout to finish: 1 out of 2 new replicas have been updated...
deployment "api" successfully rolled out
deployment "frontend" successfully rolled out

✓ sha-123a90d desplegada
```

- **Terminal 1:** se crea un pod nuevo, pasa a `Running` y solo entonces se elimina uno viejo, uno por uno (`maxSurge: 1`, `maxUnavailable: 0`).
- **Terminal 2:** todas las respuestas siguen en `HTTP 200`.

Ensayo real (PR #6, aviso "🚀 Nueva versión desplegada con CI/CD"): **149 de 149 solicitudes con HTTP 200** durante el despliegue.

### Si algo sale mal: rollback

```bash
make k8s-history     # ver revisiones
make k8s-rollback    # volver a la anterior
```

### Nota sobre la versión en Git

`make k8s-release` cambia la imagen directamente en el clúster; `deploy/kubernetes/kustomization.yaml` conserva la versión base. Para reaplicar los manifiestos sin regresar de versión:

```bash
make k8s-deploy TAG=sha-<commit>
```

En un equipo real, esta diferencia se resuelve con GitOps (Argo CD o Flux): el clúster lee la versión desde Git y se sincroniza solo.

**Mensaje para la charla:** este código se escribió hace unos minutos, pasó 7 revisiones automáticas, se empaquetó con su número de versión y Kubernetes lo desplegó sin que la página se cayera ni un segundo.

---

## Paso 8 — Observabilidad con Prometheus y Grafana (Stage 8)

**Idea:** Kubernetes sabe si los pods están vivos; la observabilidad dice **qué experimenta el usuario**: tráfico, errores y latencia.

- **Prometheus** recolecta: cada 5 s visita `/metrics` en cada pod de la API.
- **Grafana** muestra: dibuja esas métricas en un dashboard.

Se instalaron con manifiestos propios (≈ 400 MB) en lugar de `kube-prometheus-stack` (≈ 1.5-2 GB), para que cada pieza se pueda mostrar y explicar.

### Archivos

| Archivo | Qué es |
|---|---|
| `observability/prometheus/prometheus.yml` | Configuración: descubre pods del namespace `finance` con la anotación `prometheus.io/scrape: "true"` y agrega las etiquetas `pod`, `app` y `version` |
| `observability/prometheus/deployment.yaml` | ServiceAccount, permisos mínimos (solo listar pods de `finance`), Service y Deployment |
| `observability/grafana/datasources.yaml` | Conexión de Grafana con Prometheus |
| `observability/grafana/dashboards/finance-platform.json` | Dashboard versionado en Git |
| `observability/grafana/deployment.yaml` | Service y Deployment de Grafana (anónimo de solo lectura) |
| `deploy/kubernetes/api.yaml` | Anotaciones `prometheus.io/*` en los pods de la API |
| `deploy/kind/cluster.yaml` | Puertos 8090 (app), 3000 (Grafana) y 9090 (Prometheus) |
| `deploy/kind/traffic.sh` | Tráfico simulado: suscripciones, dashboards, cuentas inexistentes y health |

### Levantar todo con un comando

```bash
make demo-up      # clúster + app + Prometheus + Grafana + smoke test (≈ 3 min)
```

| Servicio | URL |
|---|---|
| Finance Platform | http://localhost:8090 |
| Grafana | http://localhost:3000 (abre directo el dashboard; usuario admin: `admin` / `opendays`) |
| Prometheus | http://localhost:9090/targets (debe mostrar los 2 pods de la API en `UP`) |

Apagar todo: `make demo-down`.

Kind solo publica puertos al crear el clúster. Si un clúster viejo no tiene el 3000 o el 9090, recrearlo con `make demo-down && make demo-up`.

### Dashboard "Finance Platform"

| Panel | Qué responde |
|---|---|
| Disponibilidad (5 min) | ¿Qué porcentaje de solicitudes no terminó en error 5xx? |
| Solicitudes por segundo | ¿Cuánto tráfico hay? |
| Latencia p95 | ¿Cuánto tarda el 95 % de las solicitudes? |
| Suscripciones (1 h) | ¿Cuántas suscripciones se crearon? (métrica de negocio) |
| **Réplicas de la API por versión** | ¿Qué versión está corriendo? Durante un Rolling Update, la anterior baja y la nueva sube |
| Solicitudes por endpoint | ¿Qué rutas se usan más? |
| Respuestas por código HTTP | 2xx éxito, 4xx error del cliente, 5xx error del servidor |
| Latencia p50 y p95 | ¿Cómo cambia el tiempo de respuesta? |

Los paneles excluyen las visitas de Prometheus (`/metrics`) y de los probes de Kubernetes (`/health`) para mostrar solo tráfico de usuarios.

### Demo: un Rolling Update visto en Grafana

```bash
# Terminal 1: tráfico simulado
make k8s-traffic

# Terminal 2: cambiar de versión (cualquier sha publicado)
make k8s-release TAG=sha-123a90d
make k8s-release                    # regresar a la última de main
```

En Grafana, el panel **Réplicas de la API por versión** muestra la transición, y **Respuestas por código HTTP** sigue sin 5xx.

Resultado del ensayo (cada 10 s):

```
hora      sha-123a90d   sha-b683f2e
20:15:31  -             2
20:15:41  2             1      ← la nueva sube, la anterior baja
20:15:51  2             -
20:16:11  1             2      ← regreso a la versión de main
20:16:21  -             2
```

### Lección aprendida: conexiones cortadas durante el Rolling Update

En el primer ensayo, con tráfico continuo, **3 de 434 solicitudes** fallaron con código `000` (conexión cortada, sin respuesta HTTP). No aparecían en los logs de Nginx: nunca llegaron a la app.

**Causa:** al apagar un pod, Kubernetes lo retira del Service de forma asíncrona. Durante un instante, la red todavía le envía conexiones nuevas a un pod que ya se está cerrando.

**Solución:** un `preStop` de 5 segundos en la API y el frontend. El pod sigue atendiendo mientras Kubernetes lo retira del Service, y después se apaga:

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sleep", "5"]
```

**Después del arreglo:** 4 releases seguidos con tráfico continuo, **576 de 576 solicitudes respondidas** (0 conexiones cortadas).

**Mensaje para la charla:** sin observabilidad no hubiéramos visto esas 3 fallas. Medir con tráfico real encontró un problema que una prueba simple no detectó.

### CI

El job **Kubernetes** también valida los manifiestos de `observability/` con kubeconform, la configuración de Prometheus con `promtool` y que el dashboard sea JSON válido.

---

## Siguiente: Paso 9 — SRE

Pendiente. SLO de disponibilidad, presupuesto de error, alerta, fallo controlado (`make demo-failure`) y runbook.
