# Estado y siguientes pasos

Última actualización: 31 de octubre de 2026.

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

## Decisiones importantes

- Finance Journal y Finance Platform son etapas del mismo producto, no proyectos independientes.
- Stage 1 se conserva separado para poder comparar la Web estática con la aplicación moderna.
- Kind será la opción principal para la futura demo de Kubernetes; Vultr puede quedar como alternativa.
- AWS se usa para demostrar una VM y Terraform, no como dependencia permanente de la charla.
- No se procesan pagos reales.
- Las cuentas, noticias modernas y valores financieros son datos de demostración.
- Los recursos cloud deben destruirse al terminar cada práctica.

## Siguiente etapa — Stage 5: DevOps y CI/CD

La siguiente implementación debe centrarse primero en **CI para Pull Requests**. Todavía no se debe automatizar un despliegue a Producción.

### 1. Preparar pruebas locales

Crear:

```text
tests/
├── api/
├── frontend/
├── infrastructure/
└── smoke/
```

Pruebas mínimas:

- Validación de los modelos y endpoints de FastAPI.
- Creación de una suscripción contra una base de datos de prueba.
- Comprobación de enlaces y archivos del frontend.
- Validación de sintaxis JavaScript.
- `terraform fmt -check` y `terraform validate`.
- Construcción de las imágenes Docker.
- Smoke test contra `/api/health`.

### 2. Inicializar Git y conectar GitHub

El directorio todavía no está preparado como repositorio Git del proyecto. Se debe:

1. Crear `.gitignore` en la raíz.
2. Excluir estados, planes, artefactos y secretos.
3. Ejecutar `git init`.
4. Crear el primer commit.
5. Crear o conectar un repositorio GitHub.

No se deben subir:

- `*.tfstate`
- `*.tfplan`
- `.terraform/`
- `.env`
- contraseñas o credenciales cloud
- paquetes generados en `build/`

### 3. Crear CI para Pull Requests

Archivo propuesto:

```text
.github/workflows/pull-request.yml
```

El pipeline debe ejecutar:

1. Validaciones de frontend.
2. Pruebas de API.
3. Pruebas de infraestructura.
4. Construcción de imágenes Docker.
5. Escaneo de dependencias y secretos.
6. Resultado obligatorio antes del merge.

### 4. Demostración esperada

```text
Crear rama
   ↓
Modificar una parte visible del dashboard
   ↓
Abrir Pull Request
   ↓
Ejecutar pruebas y seguridad
   ↓
Aprobar y hacer merge
```

### 5. Después de CI

Una vez estable el Pull Request, implementar CD:

- Crear repositorios Amazon ECR mediante Terraform.
- Publicar imágenes versionadas por commit SHA.
- Desplegar a AWS mediante SSM, sin SSH.
- Ejecutar un smoke test posterior al despliegue.
- Revertir a la versión anterior cuando falle la salud.

Después de CI/CD, continuar con:

1. Kubernetes local con Kind.
2. Prometheus, Grafana, Loki y OpenTelemetry.
3. SLI, SLO, presupuesto de error y runbook SRE.
4. Análisis de incidentes asistido por IA.

## Definición de terminado para la siguiente sesión

Stage 5A estará terminado cuando:

- Las pruebas puedan ejecutarse con un solo comando local.
- Un Pull Request ejecute automáticamente el pipeline.
- Un cambio con pruebas fallidas no pueda aprobarse.
- No existan secretos o archivos de estado en Git.
- La charla pueda mostrar rama → PR → CI → aprobación.

## Próxima instrucción sugerida

> Implementa Stage 5A: pruebas locales, `.gitignore` y workflow de CI para Pull Requests. No despliegues recursos cloud todavía.
