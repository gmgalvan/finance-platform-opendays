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

## Siguiente: Paso 7 — Del PR a Kubernetes con Rolling Update

Pendiente. Hacer un cambio visible, pasar por PR y CI, publicar la imagen nueva y actualizar `newTag` en `kustomization.yaml` para ver el Rolling Update en vivo.
