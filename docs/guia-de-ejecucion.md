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
| Jaeger | http://localhost:16686 (ver Pasos 8B y 8C) |
| Alertmanager | http://localhost:9093 (ver Paso 9) |

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

## Paso 8B — Trazas con OpenTelemetry y Jaeger

**Idea:** las métricas dicen **cuánto** tarda la API en promedio; una traza dice **por qué** tardó una solicitud concreta, paso por paso.

### Qué cambió

| Archivo | Cambio |
|---|---|
| `app/stage-2/api/main.py` | OpenTelemetry instrumenta FastAPI y psycopg, y agrega un span manual `hash_password` |
| `app/stage-2/api/requirements.txt` | Paquetes `opentelemetry-*` |
| `deploy/docker/stage-2/api.Dockerfile` | `ARG APP_VERSION`: la imagen conoce su versión |
| `.github/workflows/pull-request.yml` | Al publicar, pasa `APP_VERSION=sha-<commit>` |
| `deploy/kubernetes/api.yaml` | `OTEL_EXPORTER_OTLP_ENDPOINT` apunta a Jaeger |
| `observability/jaeger/deployment.yaml` | Jaeger v2 all-in-one (trazas en memoria) |
| `observability/grafana/datasources.yaml` | Jaeger como segunda fuente de datos en Grafana |
| `deploy/kind/cluster.yaml` | Puerto 16686 para la interfaz de Jaeger |

El tracing **solo se activa** si existe `OTEL_EXPORTER_OTLP_ENDPOINT`. Sin esa variable (pruebas, Docker Compose), la API funciona igual que antes.

Las llamadas a `/health` y `/metrics` no generan trazas: los probes y Prometheus las hacen cada pocos segundos y solo serían ruido.

`/api/health` ahora también responde la versión:

```bash
curl localhost:8090/api/health
# {"status":"ok","service":"finance-api","version":"sha-xxxxxxx","database":"connected"}
```

### Ver una traza

1. Generar tráfico: `make k8s-traffic` o crear una suscripción desde http://localhost:8090/subscribe.html.
2. Abrir http://localhost:16686.
3. **Service:** `finance-api` → **Operation:** `POST /api/subscriptions` → **Find Traces**.
4. Abrir una traza.

**Resultado del ensayo:**

```
POST /api/subscriptions          99.7 ms
  hash_password                  82.4 ms   ← 83 % del tiempo
  INSERT  (users)                 1.9 ms
  DELETE  (user_interests)        0.9 ms
  INSERT  (user_interests)        0.9 ms
  INSERT  (subscriptions)         0.9 ms
```

Al hacer clic en un `INSERT`, Jaeger muestra la consulta SQL completa.

**Mensaje para la charla (≈ 30 s):** la suscripción tarda 100 ms y la base de datos no es la culpable. El 83 % del tiempo es el hash de la contraseña, y es **a propósito**: PBKDF2 con 210 000 iteraciones hace costoso adivinar contraseñas robadas. Sin la traza, alguien podría "optimizar" la base de datos sin ningún efecto.

### Probar una imagen local antes del PR

Para validar cambios de la API sin pasar por GHCR:

```bash
docker build -f deploy/docker/stage-2/api.Dockerfile --build-arg APP_VERSION=sha-local \
  -t ghcr.io/gmgalvan/finance-platform-api:sha-local .
kind load docker-image ghcr.io/gmgalvan/finance-platform-api:sha-local --name finance
kubectl -n finance set image deployment/api api=ghcr.io/gmgalvan/finance-platform-api:sha-local
```

Después, regresar a una versión publicada con `make k8s-release`.

---

## Paso 8C — Traza completa: navegador → Nginx → API → PostgreSQL

**Idea:** en el Paso 8B la traza empezaba en la API. Ahora empieza **en el navegador**, en el momento en que el usuario hace clic, y muestra cada salto.

```
Navegador ──► Nginx ──► API ──► PostgreSQL
finance-web   finance-nginx   finance-api   (consultas SQL)
```

### Cómo se conecta

1. **Navegador** (`app/stage-2/frontend/tracing.js`, sin librerías):
   - `tracedFetch()` funciona como `fetch()`, pero crea un identificador de traza y lo envía en el encabezado estándar W3C `traceparent`.
   - Al terminar, envía su span (`Suscribirse` o `Cargar dashboard`) en formato OTLP/JSON a `/v1/traces`.
2. **Nginx** (`deploy/docker/stage-2/nginx.conf.template`):
   - Usa la imagen oficial `nginx:1.27-alpine-otel`, que ya trae el módulo de OpenTelemetry.
   - Lee el `traceparent`, crea su propio span y lo pasa a la API (`otel_trace_context propagate`).
   - Reenvía `/v1/traces` a Jaeger, así el navegador no necesita hablar con Jaeger directamente (sin problemas de CORS).
   - Escribe el `trace_id` en cada línea del access log.
3. **API y PostgreSQL:** igual que en el Paso 8B. La API continúa la traza que recibe.

### Encendido solo donde hay Jaeger

La configuración de Nginx es una **plantilla**: la imagen reemplaza variables de entorno al arrancar.

| Variable | Por defecto (Compose, CI, EC2) | En Kubernetes |
|---|---|---|
| `OTEL_TRACE` | `off` | `on` |
| `OTEL_EXPORTER_ENDPOINT` | `localhost:4317` | `jaeger.monitoring.svc.cluster.local:4317` |
| `OTLP_HTTP_COLLECTOR` | `http://127.0.0.1:4318` | `http://jaeger.monitoring.svc.cluster.local:4318` |

Sin Jaeger, Nginx arranca igual y `/v1/traces` responde 502 sin afectar a la app.

### Ver la traza completa

1. Abrir http://localhost:8090/subscribe.html y crear una cuenta.
2. Abrir http://localhost:16686.
3. **Service:** `finance-web` → **Find Traces** → abrir la traza `Suscribirse`.

**Resultado del ensayo:**

```
[finance-web]   Suscribirse                  131.3 ms   ← lo que esperó el usuario
  [finance-nginx] POST /api/subscriptions    106.0 ms
    [finance-api] POST /api/subscriptions    104.6 ms
      [finance-api] hash_password             85.2 ms
      [finance-api] INSERT                     2.5 ms
      [finance-api] DELETE                     1.2 ms
      [finance-api] INSERT                     1.0 ms
      [finance-api] INSERT                     0.8 ms
```

- Diferencia entre navegador y Nginx (≈ 25 ms): red y navegador.
- Diferencia entre Nginx y API (≈ 1.5 ms): el salto del proxy.
- En la vista **System Architecture** de Jaeger aparece el mapa `finance-web → finance-nginx → finance-api`.

### De un log a su traza

```bash
kubectl -n finance logs -l app.kubernetes.io/name=frontend --tail=20 | grep subscriptions
# ... "POST /api/subscriptions HTTP/1.1" 201 ... trace_id=d35c702ecf03a5af0807ac5591d5ca59
```

Copiar ese `trace_id` en el buscador de Jaeger (arriba a la izquierda) abre la traza exacta.

**Mensaje para la charla:** el usuario esperó 131 ms. Con una sola traza se ve cuánto fue red, cuánto proxy, cuánto API y cuánto base de datos, y que el 65 % es el hash de seguridad.

---

## Paso 8D — Un servicio nuevo: market-data

**Idea:** agregar un segundo servicio de backend y ver en Jaeger cómo una solicitud cruza **4 servicios**.

**¿Por qué un servicio aparte?** Los datos de mercado vienen de otra fuente, cambian a otro ritmo y tienen otra carga que las cuentas y suscripciones. Es una razón clara para separarlo; no se separa "por moda" (diapositiva 4).

### Qué cambió

| Archivo | Cambio |
|---|---|
| `app/stage-2/market-data/market_data.py` | Servicio FastAPI: `GET /quotes` con cotizaciones simuladas de NOVA, VERD, MX50 y BONO10; latencia de 15-60 ms y, en el 5 % de los casos, 250-400 ms |
| `app/stage-2/api/main.py` | `GET /api/market/quotes` llama a market-data con httpx (la traza se propaga sola). Si market-data falla, responde 503 |
| `app/stage-2/frontend/app.js` | La tabla "Mi lista" se actualiza cada 15 s con datos en vivo; si falla, conserva los datos de ejemplo |
| `deploy/docker/stage-2/market-data.Dockerfile` | Imagen del servicio |
| `deploy/compose/stage-2/compose.yaml` | Servicio `market-data` en Docker Compose |
| `deploy/kubernetes/market-data.yaml` | Deployment (2 réplicas) y Service; Prometheus lo descubre por anotaciones |
| `.github/workflows/pull-request.yml` | Pruebas, pip-audit y publicación de la tercera imagen |
| `tests/market_data/`, `tests/api/test_market_quotes.py` | Pruebas del servicio y de la API como intermediaria |

### Ver la traza de 4 servicios

1. Abrir http://localhost:8090. Abajo de "Mi lista" aparece **● En vivo · market-data · hh:mm:ss**.
2. En Jaeger: **Service:** `finance-web` → **Operation:** `Cargar cotizaciones` → **Find Traces**.

**Resultado del ensayo:**

```
[finance-web]   Cargar cotizaciones          53.2 ms
  [finance-nginx] GET /api/market/quotes     52.0 ms
    [finance-api] GET /api/market/quotes     50.9 ms
      [finance-api] GET (httpx)              42.8 ms
        [market-data] GET /quotes            41.5 ms
          [market-data] consultar_proveedor  40.4 ms   ← el proveedor externo
```

**System Architecture** en Jaeger:

```
finance-web → finance-nginx → finance-api → market-data
```

Buscar trazas lentas: en Jaeger, **Min Duration** = `200ms`. Aparecen las respuestas lentas del proveedor (atributo `market_data.slow_response = true`).

### Desplegar las 3 imágenes

`make k8s-release` ahora actualiza `api`, `frontend` y `market-data` a la misma versión.

### Probar imágenes locales en Kind

```bash
for c in api frontend market-data; do
  docker build -f deploy/docker/stage-2/$c.Dockerfile --build-arg APP_VERSION=sha-local \
    -t ghcr.io/gmgalvan/finance-platform-$c:sha-local .
  kind load docker-image ghcr.io/gmgalvan/finance-platform-$c:sha-local --name finance
done
make k8s-deploy TAG=sha-local
```

**Mensaje para la charla:** con una sola traza se ve que los 50 ms de la tabla de cotizaciones son, casi completos, la espera al proveedor externo. Ni la API ni Nginx son el problema.

---

## Paso 9 — SRE: SLO, alertas, fallo controlado y runbook

**Idea:** tener dashboards no basta. SRE define **qué tan confiable debe ser** el servicio, **avisa** cuando eso está en riesgo y da un **procedimiento** para arreglarlo.

### SLI, SLO y presupuesto de error

| SLI (lo que se mide) | SLO (la meta) |
|---|---|
| Disponibilidad: % de solicitudes de usuarios sin error 5xx | **99 %** |
| Latencia: % de solicitudes en menos de 500 ms | **95 %** |

- **Presupuesto de error:** con 99 %, se puede fallar el 1 %. Mientras quede presupuesto, se lanzan cambios; si se agota, se prioriza la estabilidad.
- **Velocidad de consumo:** 1 = se gasta al ritmo permitido; 10 = diez veces más rápido.

En producción el SLO se mide en 30 días y las alertas usan ventanas de 1 h y 6 h. **Para la demo** se usan ventanas de 1 y 5 minutos, y el presupuesto se calcula sobre la última hora.

### Archivos

| Archivo | Qué es |
|---|---|
| `observability/prometheus/rules.yml` | Reglas que calculan SLI, consumo y presupuesto; alertas `AltaTasaDeErrores` y `LatenciaAlta` |
| `observability/prometheus/rules_test.yml` | Pruebas unitarias de las alertas (`promtool test rules`) |
| `observability/alertmanager/` | Alertmanager: agrupa alertas y suprime `LatenciaAlta` si ya hay `AltaTasaDeErrores` |
| `observability/grafana/generate_dashboard.py` | Genera el dashboard; ahora con la fila **SLO** |
| `app/stage-2/market-data/market_data.py` | Variable `FAILURE_RATE` para simular un mal cambio de configuración |
| `docs/runbooks/alta-tasa-de-errores.md` | Runbook de la alerta principal |
| `docs/runbooks/latencia-alta.md` | Runbook de latencia |
| `docs/runbooks/retrospectiva-plantilla.md` | Plantilla de retrospectiva sin culpa, con el ejemplo del ensayo |

### Alertas

| Alerta | Se dispara cuando | Severidad |
|---|---|---|
| `AltaTasaDeErrores` | El presupuesto se consume más de 5 veces más rápido de lo permitido (más del 5 % de errores), en las ventanas de 5 min y 1 min, durante 1 min | `page`: despertar a la guardia |
| `LatenciaAlta` | Menos del 95 % responde en menos de 500 ms durante 2 min | `ticket`: atender en horario laboral |

Cada alerta incluye un enlace a su runbook.

### URLs

| | |
|---|---|
| Grafana, fila **SLO** | http://localhost:3000 |
| Alertas en Prometheus | http://localhost:9090/alerts |
| Alertmanager | http://localhost:9093 |

### Comandos

| Comando | Qué hace |
|---|---|
| `make demo-failure` | `market-data` falla el 50 % de las veces (cambio de configuración `FAILURE_RATE=0.5`) |
| `make demo-recover` | Rollback de `market-data` a la revisión anterior |
| `make alerts` | Lista las alertas activas |

### Guion de la demo (≈ 5 min)

Pantalla: Grafana (fila SLO) y una terminal.

```bash
make k8s-traffic &         # tráfico; todo en verde, presupuesto al 100 %
make demo-failure          # "alguien cambió una configuración"
```

1. En Grafana, **Disponibilidad vs SLO** cae debajo de 99 % y la **velocidad de consumo** sube.
2. A los ≈ 2 minutos: **Alertas activas = 1**. Mostrar http://localhost:9093.
3. Abrir el runbook (`docs/runbooks/alta-tasa-de-errores.md`) y seguirlo:
   - Grafana → **Respuestas por código HTTP**: los 503 son de `/api/market/quotes`.
   - Jaeger → Service `market-data`, Tags `error=true`: el error viene de market-data.
   - `kubectl -n finance rollout history deployment/market-data`: la última revisión es `Config: FAILURE_RATE=0.5`.
4. Mitigar:

```bash
make demo-recover
```

5. En ≈ 1 minuto, los errores bajan a 0 y la alerta se resuelve.
6. Cerrar con la retrospectiva: mostrar el ejemplo de `docs/runbooks/retrospectiva-plantilla.md`.

### Resultado del ensayo

```
[  0s] Tráfico iniciado (línea base)
[ 90s] disponibilidad 100 %  consumo 0  presupuesto 100 %
[ 90s] make demo-failure
[215s] 🔥 AltaTasaDeErrores FIRING  (120 s después del fallo)
[225s] disponibilidad 91.3 %  consumo 5m 8.7  consumo 1m 13.0  presupuesto 0 %
       errores: /api/market/quotes 503
       rollout history: 3  Config: FAILURE_RATE=0.5
[226s] make demo-recover
[289s] ✅ Alerta resuelta  (56 s después del rollback)
```

**Detección: 2 min · Mitigación: 18 s después de la alerta · Recuperación: 1 min.**

Durante todo el incidente, suscripciones y dashboard siguieron respondiendo (231 suscripciones creadas). Solo falló la tabla de cotizaciones, que mostró los datos de ejemplo.

El presupuesto de la última hora llega a 0 % muy rápido porque el clúster recién creado tiene pocos minutos de historia: unos minutos de errores pesan mucho. Con horas de tráfico previo, el mismo incidente consumiría solo una parte.

### Pruebas de las alertas

```bash
docker run --rm -v "$PWD/observability/prometheus:/cfg:ro" -w /cfg --entrypoint promtool \
  prom/prometheus:v3.1.0 test rules rules_test.yml
```

Comprueban que: sin errores no hay alerta; con 20 % de errores sí; y los errores de `/health` (probes) no cuentan. El CI las ejecuta en cada PR.

**Mensaje para la charla:** la página no se cayó; falló una parte y el resto siguió funcionando. Prometheus avisó antes que cualquier usuario, el runbook dijo qué revisar y un rollback lo arregló en segundos. Lo que se gastó fue presupuesto de error, y eso decide si mañana se lanzan cambios o se invierte en estabilidad.

---

## Siguiente: Paso 10 — Operaciones asistidas por IA

Pendiente. Entregar a un asistente las métricas, alertas y trazas del incidente, pedirle un resumen y posibles causas sin permiso para desplegar, y evaluar su respuesta contra la causa real.
