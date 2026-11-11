# Estado y siguientes pasos

Última actualización: 10 de noviembre de 2026.

## Objetivo del proyecto

Construir la demostración para la charla **Cloud & DevOps Essentials: How Modern Apps Work**. La historia sigue la evolución de un mismo producto financiero:

```text
Finance Journal de 1998
        ↓
Aplicación moderna de tres capas
        ↓
Contenedores y despliegue en AWS
        ↓
CI/CD, Kubernetes, SRE y AIOps
```

La charla está diseñada para durar 50 minutos: 42 minutos de contenido y demostraciones, más 8 minutos para preguntas.

## Estado actual

### Stage 1 — Sitio estático de 1998: terminado

Una publicación financiera construida con HTML y CSS. Incluye noticias financieras históricas, diseño inspirado en la Web de los años noventa y una configuración de Nginx con logs y endpoint de salud.

Archivos principales:

- `app/frontend/index.html`
- `app/frontend/styles.css`
- `deploy/docker/stage-1/Dockerfile`
- `deploy/docker/stage-1/default.conf`
- `docs/stage-1-static-web.md`

Ejecutar directamente:

```bash
make serve-static
```

Abrir `http://localhost:8080`.

Ejecutar con Nginx:

```bash
make docker-build-static
make docker-run-static
```

### Stage 2 — Aplicación de tres capas: terminado

Finance Platform incluye un dashboard moderno, portafolio, metas, noticias, lista de seguimiento y un flujo de suscripción.

Arquitectura:

```text
Navegador
   ↓
Nginx / Frontend
   ↓ HTTP y JSON
FastAPI / Python
   ↓ SQL
PostgreSQL
```

Archivos principales:

- `app/stage-2/frontend/`
- `app/stage-2/api/main.py`
- `app/stage-2/database/init.sql`
- `deploy/compose/stage-2/compose.yaml`
- `deploy/docker/stage-2/`
- `docs/stage-2-finance-platform.md`

Ejecutar solo el frontend:

```bash
make serve-stage-2
```

Abrir `http://localhost:8081`. En este modo el formulario no puede guardar cuentas.

Ejecutar las tres capas:

```bash
make stage-2-up
```

Abrir `http://localhost:8082`.

Comandos operativos:

```bash
make stage-2-logs
make stage-2-down
```

Funcionalidad verificada:

- Creación y actualización de usuarios.
- Suscripción `finance_plus`.
- Preferencias financieras persistidas.
- Contraseñas protegidas con PBKDF2 y salt aleatorio.
- Dashboard personalizado.
- `GET /api/health` conectado a PostgreSQL.
- `GET /api/metrics` en formato Prometheus.

### Stage 3 — AWS EC2 con Terraform: implementado y destruido

Se creó y verificó un despliegue real en AWS `us-east-1`:

- EC2 `t3.micro` con Amazon Linux 2023.
- Disco gp3 cifrado.
- Nginx, FastAPI y PostgreSQL en Docker.
- Bucket S3 privado para entregar el artefacto.
- Rol IAM y administración mediante Systems Manager.
- IMDSv2 obligatorio.
- Puerto HTTP abierto y SSH cerrado.

La página, el endpoint de salud, las métricas y la escritura/lectura en PostgreSQL se probaron correctamente.

Los recursos de AWS fueron destruidos para detener los cargos. El estado local de Terraform no contiene actualmente recursos administrados. Las direcciones IP utilizadas durante la prueba ya no son válidas.

Archivos principales:

- `infra/terraform/aws-ec2/`
- `infra/terraform/aws-ec2/user-data.sh.tftpl`
- `docs/stage-3-aws-ec2.md`

Recrear la infraestructura únicamente cuando sea necesario:

```bash
make package-stage-3
make terraform-stage-3-init
make terraform-stage-3-plan
make terraform-stage-3-apply
```

Eliminarla al terminar:

```bash
make terraform-stage-3-destroy
```

### Stage 4 — Contenedores e infraestructura como código: cubierto

Esta etapa de la narrativa ya quedó incorporada en Stages 2 y 3:

- Dockerfiles reproducibles para frontend y API.
- PostgreSQL ejecutándose como contenedor con volumen persistente.
- Docker Compose para el ambiente local.
- Terraform para construir y eliminar la infraestructura AWS.
- Bootstrap versionado para instalar y ejecutar la aplicación en EC2.

Por esa razón, el siguiente bloque de implementación es Stage 5 y no hace falta crear otra aplicación para Stage 4.

### Stage 5A — Pruebas y CI para Pull Requests: terminado

Repositorio: https://github.com/gmgalvan/finance-platform-opendays

Pruebas en `tests/`:

| Carpeta | Qué revisa |
|---|---|
| `tests/api/` | Validaciones, hash PBKDF2, `/health` y `/metrics` (unitarias) y suscripción + dashboard contra PostgreSQL (integración) |
| `tests/frontend/` | Enlaces, recursos y anclas locales, `lang`/`title` y sintaxis JavaScript |
| `tests/infrastructure/` | Políticas de seguridad sobre Terraform: sin SSH, IMDSv2, disco y bucket cifrados, bucket privado |
| `tests/smoke/smoke.sh` | Recorrido completo contra la aplicación en ejecución |

Comandos locales:

```bash
make test-setup   # crea .venv con Python 3.12 usando uv
make test-db-up   # PostgreSQL de pruebas en el puerto 55432 (requiere Docker)
make test         # pytest + terraform fmt/validate
make test-db-down
make smoke        # contra make stage-2-up
```

Sin PostgreSQL, las pruebas de integración se omiten localmente. En CI se define `REQUIRE_DATABASE=1` para que fallen en lugar de omitirse.

Workflow `.github/workflows/pull-request.yml`, que corre en cada Pull Request y en cada push a `main`:

| Job | Qué hace |
|---|---|
| Frontend | Pruebas de `tests/frontend` con Node.js 22 |
| API + PostgreSQL | Pruebas de `tests/api` con PostgreSQL 17 como servicio |
| Terraform | `fmt -check`, `validate` y políticas de `tests/infrastructure` |
| Seguridad | gitleaks (secretos en el historial), pip-audit y dependency review en PRs |
| Docker + smoke test | Construye las imágenes, levanta las tres capas y ejecuta `smoke.sh` |
| CI passed | Falla si cualquier job anterior falla; es el check obligatorio |

Protección de `main`:

- `CI passed` es obligatorio y la rama debe estar actualizada.
- Aplica también a administradores.
- Sin force push ni borrado de la rama.
- Conversaciones resueltas antes del merge.
- No exige aprobaciones porque el proyecto tiene un solo autor.

También están activadas las alertas de Dependabot, que habilitan el Dependency graph requerido por dependency review.

Ensayos realizados:

- PR #1: agrega pruebas y CI. Todos los jobs en verde, merge permitido.
- PR #2: abre el puerto 22 a `0.0.0.0/0`. `terraform validate` pasa, pero la política `test_ssh_port_is_not_open` falla y GitHub bloquea el merge, incluso para el administrador. Se cerró sin merge.

El pipeline completo tarda menos de un minuto.

## Decisiones importantes

- Finance Journal y Finance Platform son etapas del mismo producto, no proyectos independientes.
- Stage 1 se conserva separado para poder comparar la Web estática con la aplicación moderna.
- Kind será la opción principal para la futura demo de Kubernetes; Vultr puede quedar como alternativa.
- AWS se usa para demostrar una VM y Terraform, no como dependencia permanente de la charla.
- No se procesan pagos reales.
- Las cuentas, noticias modernas y valores financieros son datos de demostración.
- Los recursos cloud deben destruirse al terminar cada práctica.
- Todo cambio llega a `main` mediante Pull Request y CI en verde.

## Siguiente etapa — Stage 5B: entrega continua

Propuesta para la charla: publicar imágenes en **GitHub Container Registry (GHCR)** en lugar de Amazon ECR. No requiere credenciales de AWS ni genera costos, y las imágenes quedan listas para Kind en Stage 6.

1. Al hacer merge en `main`, construir las imágenes de frontend y API.
2. Etiquetarlas con el commit SHA y publicarlas en `ghcr.io/gmgalvan/...`.
3. Firmar o registrar la procedencia de la imagen (opcional).
4. Mostrar en la charla que la misma imagen se promueve entre ambientes.

El despliegue a AWS mediante ECR + SSM queda como alternativa documentada, no como parte de la demo en vivo.

Después de CD, continuar con:

1. Kubernetes local con Kind.
2. Prometheus, Grafana, Loki y OpenTelemetry.
3. SLI, SLO, presupuesto de error y runbook SRE.
4. Análisis de incidentes asistido por IA.

## Próxima instrucción sugerida

> Implementa Stage 5B: workflow que publique en GHCR las imágenes de frontend y API etiquetadas con el commit SHA al hacer merge en `main`.
