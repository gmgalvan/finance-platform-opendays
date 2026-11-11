# Cloud & DevOps Essentials: How Modern Apps Work

## Estructura de la charla

## Objetivo

Explicar de forma sencilla cómo evolucionan las aplicaciones modernas y cómo Cloud, DevOps, Kubernetes y SRE ayudan a construirlas, probarlas, desplegarlas y operarlas de manera confiable.

## Aplicación para la demostración

Una **plataforma de información financiera por suscripción**. La aplicación puede mostrar noticias o indicadores financieros, permitir que un usuario se suscriba y consultar un pequeño dashboard.

Componentes mínimos para la demo:

- Frontend web con una página de inicio y un dashboard.
- API para consultar información financiera.
- Base de datos para usuarios y suscripciones.
- Endpoint `/health` y métricas para demostrar observabilidad.
- Un cambio visual sencillo que pueda recorrer todo el flujo de entrega.

La demo no necesita implementar pagos reales. Una suscripción simulada mantiene el foco en arquitectura y DevOps.

## Estructura propuesta — 8 diapositivas

### 1. Una idea sencilla en la web

**Historia:** una persona apasionada por la economía crea una página estática para compartir información financiera.

- HTML y CSS servidos desde una sola máquina.
- La aplicación y la infraestructura son simples.
- Pregunta guía: ¿qué ocurre cuando llegan usuarios y nuevas necesidades?

**Tecnologías:** HTML, CSS, servidor web y Git.

**Sistema operativo:** Linux, por ejemplo Ubuntu Server, instalado directamente en una máquina física o virtual.

**Métricas y observabilidad:** revisión manual, logs de acceso y errores de Apache/Nginx, comandos como `top`, `df` y `free`, y comprobaciones básicas de disponibilidad.

### 2. De página estática a aplicación de tres capas

La página comienza a ofrecer cuentas, suscripciones, contenido personalizado y productos.

- Frontend para la experiencia del usuario.
- Backend para las reglas del negocio.
- Base de datos para usuarios, contenido y suscripciones.
- Crecimiento vertical frente a crecimiento horizontal.

**Tecnologías:** React o una interfaz web sencilla, API con Node.js o Python, PostgreSQL y Nginx.

**Sistema operativo:** Linux en uno o varios servidores; cada equipo administra actualizaciones, procesos, usuarios y paquetes del sistema.

**Métricas y observabilidad:** logs separados de frontend, backend, Nginx y PostgreSQL; monitoreo de CPU, memoria, disco, latencia, errores HTTP y conexiones a la base de datos. Herramientas típicas: `systemd`/`journalctl`, Nagios o Zabbix.

### 3. De servidores propios a la nube

La demanda cambia y comprar servidores deja de ser práctico.

- Máquinas virtuales, almacenamiento de objetos y bases de datos administradas.
- Balanceo de carga y colas cuando aumenta la concurrencia.
- La arquitectura evoluciona según las necesidades; no por moda.

**Tecnologías:** AWS EC2, S3, RDS, Load Balancer y SQS. Vultr puede usarse como nube para el laboratorio.

**Sistema operativo:** imágenes Linux preconfiguradas para las máquinas virtuales, como Ubuntu Server o Amazon Linux. Algunos servicios administrados ocultan la gestión directa del sistema operativo.

**Métricas y observabilidad:** métricas centralizadas de CPU, red, disco, balanceadores, base de datos y colas; alarmas por umbrales y logs enviados a un servicio común. En AWS: CloudWatch Metrics, Logs y Alarms; en Vultr: métricas de las instancias y alertas.

**Demo breve:** enseñar una instancia creada manualmente para evidenciar el punto de partida y sus limitaciones.

### 4. Infraestructura repetible y aplicaciones portables

Crear recursos manualmente es lento y difícil de reproducir.

- Infraestructura como código para versionar y repetir ambientes.
- Contenedores para ejecutar la aplicación de la misma manera en cualquier entorno.
- Paso de una aplicación monolítica a servicios únicamente cuando existe una razón clara.

**Tecnologías:** Terraform, Docker, registro de imágenes y GitHub.

**Sistema operativo:** Linux continúa como sistema anfitrión, mientras cada contenedor incluye solamente el espacio de usuario y las dependencias que necesita. Todos los contenedores comparten el kernel del host.

**Métricas y observabilidad:** logs enviados a la salida estándar del contenedor, métricas de consumo por imagen o servicio, salud mediante `HEALTHCHECK` y trazabilidad de qué versión se está ejecutando. Herramientas iniciales: `docker logs`, `docker stats` y métricas del proveedor cloud.

**Demo breve:** mostrar el código de Terraform y construir la imagen de la aplicación.

### 5. DevOps y el camino de un cambio

Desarrollo y operaciones trabajan sobre un flujo compartido.

- Crear una rama y un Pull Request.
- Ejecutar validaciones, pruebas y análisis de seguridad.
- Aprobar y hacer merge.
- Promover la misma versión por Dev, UAT/QA y Producción.

**Tecnologías:** GitHub, GitHub Actions, pruebas automatizadas, escaneo de dependencias y secrets.

**Sistema operativo:** runners efímeros de Linux para compilar, probar y empaquetar la aplicación; los ambientes se describen como código para reducir diferencias entre Dev, UAT/QA y Producción.

**Métricas y observabilidad:** duración y tasa de éxito de builds y despliegues, cobertura de pruebas, vulnerabilidades, frecuencia de despliegue, tiempo de entrega, tasa de fallos y tiempo de recuperación. GitHub Actions conserva logs y resultados de cada ejecución.

**Demo principal:** hacer un cambio visible, abrir el PR y observar el pipeline de CI.

### 6. Kubernetes, despliegue y observabilidad

Cuando existen varios contenedores, se necesita automatizar su operación.

- Kubernetes mantiene el estado deseado, escala y recupera cargas.
- Despliegues Rolling Update, Blue/Green o Canary reducen el riesgo.
- Métricas, logs y trazas permiten saber qué sucede después del despliegue.

**Tecnologías:** Kubernetes, `kubectl`, Kind para la demo local o Vultr Kubernetes, Helm, Prometheus y Grafana.

**Sistema operativo:** nodos Linux que ejecutan el runtime de contenedores y Kubernetes. En un servicio administrado, el proveedor mantiene el plano de control; con Kind, los nodos se simulan mediante contenedores locales.

**Métricas y observabilidad:** Prometheus recolecta métricas de la aplicación y del clúster; Grafana presenta dashboards; Loki puede centralizar logs y OpenTelemetry/Jaeger puede seguir trazas entre servicios. Se observan latencia, tráfico, errores, saturación, reinicios de pods, uso de recursos y estado de los despliegues.

**Demo principal:** desplegar la nueva versión, observar el rollout y comprobar métricas y salud de la aplicación.

### 7. SRE: convertir observabilidad en confiabilidad

Tener dashboards no es suficiente: SRE utiliza las señales del sistema para tomar decisiones y equilibrar velocidad con estabilidad.

- Definir SLI para medir lo que experimenta el usuario, como disponibilidad y latencia.
- Establecer SLO claros, por ejemplo 99.9 % de solicitudes exitosas al mes.
- Usar el presupuesto de error para decidir si se lanzan nuevas funciones o se prioriza la estabilidad.
- Crear alertas accionables, runbooks, guardias e incidentes con retrospectivas sin culpa.

**Tecnologías:** Prometheus, Grafana, Alertmanager, PagerDuty u otra herramienta de alertas y runbooks versionados en GitHub.

**Sistema operativo:** SRE opera los mismos nodos Linux y servicios de Kubernetes, pero busca automatizar tareas repetitivas y reducir el trabajo manual de operación.

**Métricas y observabilidad:** SLI/SLO, disponibilidad, latencia, tasa de errores, saturación y consumo del presupuesto de error. También se miden MTTR, incidentes repetidos y carga operativa.

**Demo breve:** provocar un fallo controlado o aumentar la latencia, observar la alerta y usar un runbook para identificar y recuperar el servicio.

### 8. El siguiente paso: operaciones asistidas por IA

La IA puede ayudar en puntos concretos, pero necesita controles y evaluación.

- Asistir en la revisión de código, diagnóstico de incidentes o resumen de observabilidad.
- Evaluar calidad, seguridad, costo y confiabilidad antes de automatizar decisiones.
- Mantener aprobación humana para cambios sensibles.
- Idea final: Cloud Native es una evolución de personas, procesos y tecnología.

**Tecnologías:** un asistente de código en vivo, LLM, evaluaciones y datos de Prometheus/Grafana.

**Sistema operativo:** la aplicación sigue operando sobre Linux y Kubernetes; la IA se integra como un servicio adicional o consume APIs administradas, sin sustituir la plataforma operativa.

**Métricas y observabilidad:** además de las métricas tradicionales, se miden latencia, costo por solicitud, consumo de tokens, calidad de respuestas, errores, alucinaciones y resultados de evaluaciones. La IA puede resumir señales o sugerir causas, pero las acciones sensibles conservan aprobación humana.

## Flujo recomendado para la demo

1. Mostrar la versión actual de la plataforma financiera.
2. Pedir al asistente de código un cambio pequeño y fácil de verificar.
3. Crear una rama, commit y Pull Request en GitHub.
4. Ejecutar pruebas y validaciones con GitHub Actions.
5. Hacer merge y generar una imagen Docker versionada.
6. Desplegarla en Kubernetes con un Rolling Update.
7. Confirmar el estado con métricas, logs y el endpoint de salud.
8. Mostrar un SLO y cómo el despliegue afecta su presupuesto de error.

## Distribución de los 50 minutos

Reservar **42 minutos para la charla y las demostraciones** y **8 minutos para preguntas**. La presentación debe avanzar aunque alguna demo tarde o falle.

| Bloque | Tiempo | Acumulado | Qué mostrar |
|---|---:|---:|---|
| Apertura | 2 min | 2 min | Objetivo y presentación de la plataforma financiera |
| Diapositiva 1: web sencilla | 3 min | 5 min | Página estática, servidor Linux y logs básicos |
| Diapositiva 2: tres capas | 4 min | 9 min | Frontend, API, base de datos y crecimiento |
| Diapositiva 3: nube | 4 min | 13 min | VM preparada, servicios cloud y CloudWatch |
| Diapositiva 4: IaC y contenedores | 5 min | 18 min | Terraform, Docker y portabilidad |
| Diapositiva 5: DevOps y CI/CD | 7 min | 25 min | Cambio, Pull Request y GitHub Actions |
| Diapositiva 6: Kubernetes | 8 min | 33 min | Despliegue, Rolling Update y observabilidad |
| Diapositiva 7: SRE | 5 min | 38 min | SLO, alerta, presupuesto de error y runbook |
| Diapositiva 8: IA | 3 min | 41 min | Resumen del incidente y evaluación de la respuesta |
| Cierre | 1 min | 42 min | Recapitulación y mensaje principal |
| Preguntas | 8 min | 50 min | Dudas del público |

### Prioridades de la demostración

- **Demos principales en vivo:** Pull Request/CI, despliegue en Kubernetes y dashboard de observabilidad.
- **Demos cortas:** fallo controlado de SRE y análisis del incidente con IA.
- **Material preparado:** creación manual de EC2/Vultr, `terraform apply`, instalación del clúster y descarga de dependencias.
- Si el tiempo se reduce, omitir la ejecución de IA y mostrar únicamente su resultado preparado.
- Establecer una alarma al minuto 38: en ese momento se debe iniciar el cierre o la última diapositiva.

## Estructura del repositorio para la demo

La demo puede mantenerse en un solo repositorio con **7 carpetas principales**. No es necesario crear un repositorio diferente para cada etapa: la evolución se muestra mediante commits, tags o ramas.

```text
finance-platform/
├── app/
│   ├── frontend/          # Página web y dashboard financiero
│   ├── api/               # API, endpoints /health y /metrics
│   ├── database/          # Esquema, migraciones y datos de ejemplo
│   └── ai-assistant/      # Integración opcional para la diapositiva 8
├── tests/                 # Pruebas unitarias, integración y smoke tests
├── infra/
│   └── terraform/         # Infraestructura como código para AWS o Vultr
├── deploy/
│   ├── docker/            # Dockerfiles y configuración local
│   ├── compose/           # Aplicación de tres capas en una máquina
│   ├── kubernetes/        # Deployments, Services, Ingress y ConfigMaps
│   └── helm/              # Chart opcional para empaquetar el despliegue
├── observability/
│   ├── prometheus/        # Recolección de métricas y reglas de alertas
│   ├── grafana/           # Dashboards versionados
│   ├── loki/              # Configuración de logs
│   └── opentelemetry/     # Trazas de la aplicación
├── docs/
│   ├── diagrams/          # Diagramas de cada etapa de arquitectura
│   └── runbooks/          # Instrucciones para responder a incidentes
└── .github/
    └── workflows/         # Pipelines de CI, seguridad y despliegue
```

Archivos importantes en la raíz:

- `README.md`: instrucciones y narrativa de la demo.
- `.env.example`: variables necesarias sin incluir secretos.
- `Makefile`: comandos cortos como `make test`, `make deploy` y `make demo-failure`.
- `.gitignore`: exclusión de secretos, estado local y archivos generados.

## Qué mostrar en cada paso de la demo

### Paso 1 — Página web sencilla

**Carpetas utilizadas:** `app/frontend/` y `docs/diagrams/`.

- Abrir una versión estática de la página financiera.
- Mostrar que todo puede servirse desde una sola máquina Linux con Nginx.
- Consultar los access logs y ejecutar `top`, `free` o `df`.
- Tag sugerido: `stage-1-static-web`.

### Paso 2 — Aplicación de tres capas

**Carpetas utilizadas:** `app/frontend/`, `app/api/`, `app/database/` y `deploy/compose/`.

- Iniciar frontend, API y PostgreSQL con Docker Compose.
- Crear una suscripción simulada y consultar el dashboard.
- Mostrar logs separados, latencia de la API y conexiones a la base de datos.
- Tag sugerido: `stage-2-three-tier`.

### Paso 3 — Migración a la nube

**Carpetas utilizadas:** `docs/diagrams/` y, como preparación para la siguiente etapa, `infra/terraform/`.

- Enseñar una EC2 o VM de Vultr creada manualmente.
- Desplegar la misma aplicación y explicar escalamiento vertical y horizontal.
- Mostrar métricas y alarmas de CloudWatch o del proveedor elegido.
- No crear todos los recursos en vivo; usar una instancia preparada.
- Tag sugerido: `stage-3-cloud-vm`.

### Paso 4 — Infraestructura como código y contenedores

**Carpetas utilizadas:** `infra/terraform/`, `deploy/docker/` y `deploy/compose/`.

- Comparar la creación manual con un `terraform plan`.
- Construir una imagen Docker versionada y ejecutarla localmente.
- Mostrar `docker logs`, `docker stats` y el `HEALTHCHECK`.
- Tag sugerido: `stage-4-iac-containers`.

### Paso 5 — Pull Request y CI/CD

**Carpetas utilizadas:** `.github/workflows/` y `tests/`.

- Hacer un cambio visual pequeño con un asistente de código.
- Crear una rama y abrir un Pull Request.
- Ejecutar lint, pruebas, escaneo de seguridad y build de la imagen.
- Hacer merge y promover la misma versión por Dev, UAT y Producción.
- Tag sugerido: `stage-5-cicd`.

### Paso 6 — Kubernetes y observabilidad

**Carpetas utilizadas:** `deploy/kubernetes/`, `deploy/helm/` y `observability/`.

- Desplegar en Kind como opción principal o en Vultr Kubernetes.
- Ejecutar un Rolling Update y observar el estado de los pods.
- Consultar métricas en Prometheus/Grafana, logs en Loki y una traza.
- Tag sugerido: `stage-6-kubernetes`.

### Paso 7 — SRE y respuesta a incidentes

**Carpetas utilizadas:** `observability/prometheus/`, `observability/grafana/` y `docs/runbooks/`.

- Mostrar el SLO de disponibilidad y su presupuesto de error.
- Activar un fallo controlado con `make demo-failure`.
- Observar la alerta, seguir el runbook y recuperar el servicio.
- Cerrar con una retrospectiva breve: impacto, causa y prevención.
- Tag sugerido: `stage-7-sre`.

### Paso 8 — Operaciones asistidas por IA

**Carpetas utilizadas:** `app/ai-assistant/`, `observability/` y `tests/`.

- Entregar al asistente únicamente métricas, logs y trazas de la demo.
- Pedirle un resumen del incidente y posibles causas, sin darle permiso de desplegar.
- Ejecutar una evaluación preparada para comparar la respuesta con la causa real.
- Mostrar métricas de latencia, costo, tokens y calidad de la respuesta.
- Tag sugerido: `stage-8-aiops`.

## Orden de construcción recomendado

No hace falta implementar todo al mismo tiempo. Construir primero los pasos 1, 2, 5 y 6 permite tener una demo completa. Después se agregan Terraform, SRE e IA. Cada tag conserva una versión estable para poder saltar al siguiente paso si algo falla durante la presentación.

## Recomendación de alcance

Para una charla fluida, usar **Kind localmente como plan principal** y dejar Vultr como alternativa o captura preparada. Crear EC2 manualmente y después desplegar también en Vultr durante la misma sesión puede consumir demasiado tiempo y distraer del mensaje. AWS puede mostrarse en la diapositiva de evolución, mientras que la demo en vivo se concentra en GitHub Actions, Kubernetes y observabilidad.

Preparar como respaldo capturas o un video corto del pipeline y del despliegue por si falla la red o tarda la creación de infraestructura.
