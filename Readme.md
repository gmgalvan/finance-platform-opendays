# Cloud & DevOps Essentials: How Modern Apps Work

Introducción a Cloud, DevOps, Kubernetes, SRE y AIOps explicada de forma sencilla para estudiantes. La charla muestra cómo evolucionan las aplicaciones modernas y cómo las empresas utilizan automatización para construirlas, probarlas, desplegarlas y operarlas de manera confiable.

## Objetivo

Explicar la evolución de una aplicación desde una página web estática hasta una plataforma cloud native. La audiencia conocerá no solo las tecnologías, sino también los problemas que motivaron cada cambio de arquitectura y de proceso.

Al finalizar, los participantes podrán identificar:

- La diferencia entre una aplicación estática, una arquitectura de tres capas y una arquitectura distribuida.
- El paso de servidores físicos y máquinas virtuales a contenedores y Kubernetes.
- El valor de la nube y de la infraestructura como código.
- El recorrido de un cambio desde el Pull Request hasta Producción.
- El papel de las pruebas, la seguridad, la observabilidad y SRE.
- Cómo incorporar inteligencia artificial con evaluaciones y controles.

## Historia conductora

La charla comienza con una persona apasionada por la economía y las finanzas que crea una página web estática para publicar contenido. En esta primera etapa solamente necesita HTML, CSS y un servidor web.

Con el tiempo, la página comienza a ofrecer cuentas, suscripciones, contenido personalizado y productos. Para soportar estas funciones, evoluciona hacia una arquitectura de tres capas:

1. Un frontend para la experiencia del usuario.
2. Un backend para las reglas de negocio.
3. Una base de datos para usuarios, contenido y suscripciones.

Al aumentar el tráfico, la empresa necesita más capacidad. Primero escala verticalmente al mejorar el hardware y después horizontalmente al agregar servidores. La operación se vuelve más compleja y aparecen nuevas necesidades: balanceo de carga, almacenamiento de objetos, bases de datos administradas, colas y patrones para manejar concurrencia.

La nube permite consumir estos recursos bajo demanda. Posteriormente, los contenedores hacen que la aplicación sea portable y consistente entre ambientes. Dev y Ops establecen un flujo compartido de integración y entrega continua. Cuando administrar muchos contenedores se vuelve difícil, Kubernetes proporciona orquestación, escalamiento y recuperación automática.

Finalmente, la observabilidad y SRE permiten operar la plataforma mediante métricas, logs, trazas, SLO y presupuestos de error. La inteligencia artificial se incorpora como una herramienta de apoyo para revisar código o analizar incidentes, siempre acompañada de evaluaciones y aprobación humana.

## Temas principales

- Evolución de la web y de las arquitecturas de aplicaciones.
- Arquitectura de tres capas: frontend, backend y base de datos.
- Escalamiento vertical y horizontal.
- Máquinas virtuales y servicios en la nube.
- AWS EC2, S3, RDS, balanceadores y colas.
- Infraestructura como código con Terraform.
- Contenedores con Docker.
- Orquestación con Kubernetes.
- Flujo de trabajo con Git y GitHub.
- Pull Requests, revisión de código y merge.
- CI/CD con GitHub Actions.
- Ambientes de Dev, UAT/QA y Producción.
- Estrategias de despliegue: Rolling Update, Blue/Green y Canary.
- Seguridad integrada al pipeline.
- Métricas, logs y trazas con Prometheus, Grafana, Loki y OpenTelemetry.
- SRE: SLI, SLO, presupuestos de error, alertas, incidentes y runbooks.
- AIOps, agentes y evaluación de sistemas de IA.
- Automatización avanzada y el concepto de *dark factories*.

## Aplicación de demostración

La demostración utilizará una plataforma de información financiera por suscripción. La aplicación tendrá:

- Una página de inicio y un dashboard financiero.
- Una API para consultar información.
- Una base de datos para usuarios y suscripciones simuladas.
- Endpoints de salud y métricas.
- Instrumentación para logs y trazas.

No se procesarán pagos reales. La suscripción será simulada para mantener el enfoque en Cloud y DevOps.

## Recorrido de la demostración

1. Mostrar la aplicación ejecutándose inicialmente en un servidor Linux.
2. Explicar su evolución hacia una arquitectura de tres capas.
3. Comparar la creación manual de una VM con infraestructura definida en Terraform.
4. Empaquetar la aplicación en contenedores Docker.
5. Realizar un cambio pequeño con un asistente de código, por ejemplo Claude Code.
6. Crear una rama y abrir un Pull Request en GitHub.
7. Ejecutar pruebas y controles de seguridad con GitHub Actions.
8. Hacer merge y generar una imagen versionada.
9. Desplegar en Kubernetes mediante un Rolling Update.
10. Validar el estado con métricas, logs, trazas y un endpoint de salud.
11. Provocar un fallo controlado y responder mediante una alerta y un runbook.
12. Utilizar IA para resumir el incidente y evaluar la calidad de su respuesta.

Para reducir riesgos durante la presentación, la creación de infraestructura cloud estará preparada con anticipación. La parte principal de la demo se ejecutará en Kind localmente; Vultr Kubernetes podrá utilizarse como alternativa. AWS se empleará para explicar la evolución hacia la nube y mostrar una instancia o evidencia previamente preparada.

## Duración

La sesión dura **50 minutos**:

- 42 minutos de charla y demostraciones.
- 8 minutos para preguntas.

Las demostraciones prioritarias son el flujo de Pull Request y CI/CD, el despliegue en Kubernetes y la observabilidad. Terraform, SRE e IA se mostrarán de forma breve para conservar tiempo para las dudas del público.

## Estructura detallada

La organización de las ocho diapositivas, el tiempo asignado, la estructura del repositorio y los pasos de la demo se encuentran en [talk-structure.md](./talk-structure.md).

## Estado de implementación

### Stage 1 — Static web

La primera versión ya está disponible en [`app/frontend`](./app/frontend). Representa una publicación financiera de finales de los años noventa construida solamente con HTML y CSS.

Para ejecutarla localmente:

```bash
make serve-static
```

Después, abrir `http://localhost:8080`. También se incluye una imagen de Nginx con access logs, error logs y un endpoint de salud. Las instrucciones completas están en [docs/stage-1-static-web.md](./docs/stage-1-static-web.md).

### Stage 2 — Finance Platform

La evolución moderna está disponible en [`app/stage-2/frontend`](./app/stage-2/frontend). Incluye un dashboard, portafolio, meta de ahorro, lista de seguimiento, noticias y una suscripción simulada.

Para revisar solamente el frontend:

```bash
make serve-stage-2
```

Después, abrir `http://localhost:8081`. Este modo no guarda cuentas.

Para iniciar la arquitectura completa con Nginx, API y PostgreSQL:

```bash
make stage-2-up
```

Después, abrir `http://localhost:8082`. Consulta [docs/stage-2-finance-platform.md](./docs/stage-2-finance-platform.md) para conocer los servicios, logs y comandos disponibles.

### Stage 3 — AWS EC2 con Terraform

El módulo [`infra/terraform/aws-ec2`](./infra/terraform/aws-ec2) despliega Finance Platform en una instancia Amazon Linux 2023. Utiliza un bucket privado para entregar el artefacto, un rol de instancia para SSM y un security group sin acceso SSH.

Las instrucciones de creación, verificación y eliminación se encuentran en [docs/stage-3-aws-ec2.md](./docs/stage-3-aws-ec2.md).

### Stage 5 — Pruebas y CI

Repositorio: https://github.com/gmgalvan/finance-platform-opendays

Cada Pull Request ejecuta GitHub Actions con pruebas de frontend, API con PostgreSQL, validación y políticas de Terraform, escaneo de seguridad y un smoke test con Docker Compose. La rama `main` exige que el check **CI passed** esté en verde antes del merge.

Para ejecutar las pruebas localmente:

```bash
make test-setup
make test-db-up   # opcional, requiere Docker
make test
```

El detalle de cada job se encuentra en [specs/README.md](./specs/README.md) y el paso a paso para repetir todo en [docs/guia-de-ejecucion.md](./docs/guia-de-ejecucion.md).
