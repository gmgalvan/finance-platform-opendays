# Stage 2: Finance Platform

Esta etapa muestra la evolución de Finance Journal hacia una plataforma financiera moderna con cuentas, contenido personalizado y una suscripción.

## Arquitectura

```text
Navegador
   │ HTTP :8082
   ▼
Nginx / Frontend
   │ /api/*
   ▼
API de Python :8000
   │ SQL
   ▼
PostgreSQL :5432
```

Los puertos de la API y PostgreSQL solo están disponibles dentro de la red de Docker. El navegador accede a todo mediante Nginx en `http://localhost:8082`.

## Funcionalidad

- Dashboard personalizado.
- Valor y distribución del portafolio con datos ficticios.
- Meta de ahorro y gráfico interactivo.
- Lista de seguimiento y noticias.
- Flujo de creación de cuenta en tres pasos.
- Registro real de usuarios, preferencias y suscripciones en PostgreSQL.
- Contraseñas de demostración protegidas con PBKDF2 y salt aleatorio.
- Endpoints de salud y métricas Prometheus.

No se procesan pagos reales. Los datos son exclusivamente para una demostración local.

## Ejecutar el frontend solamente

```bash
make serve-stage-2
```

Abrir `http://localhost:8081`. Este modo permite revisar la interfaz, pero el formulario no puede guardar cuentas porque no existen API ni PostgreSQL.

## Ejecutar las tres capas con Docker

```bash
make stage-2-up
```

Abrir `http://localhost:8082` y completar el flujo **Conocer el plan**.

Docker inicia:

- `frontend`: Nginx sirve HTML, CSS y JavaScript y actúa como reverse proxy.
- `api`: FastAPI valida solicitudes, aplica reglas y consulta la base de datos.
- `db`: PostgreSQL almacena usuarios, intereses y suscripciones.

## Operación

Ver los logs de todos los servicios:

```bash
make stage-2-logs
```

Detener los contenedores sin borrar la información:

```bash
make stage-2-down
```

La información permanece en el volumen `stage-2_finance_postgres_data`.

## Endpoints

- `GET /api/health`: salud de la API y su conexión a PostgreSQL.
- `POST /api/subscriptions`: crea o actualiza una cuenta y su suscripción.
- `GET /api/dashboard?email=...`: recupera el perfil personalizado.
- `GET /api/metrics`: métricas de solicitudes y latencia en formato Prometheus.

## Qué mostrar durante la charla

1. Ejecutar `make stage-2-up` antes de comenzar la sesión.
2. Abrir el formulario y crear una cuenta ficticia.
3. Mostrar la solicitud `POST /api/subscriptions` en las herramientas del navegador.
4. Regresar al dashboard y comprobar el nombre personalizado.
5. Ejecutar `make stage-2-logs` para comparar logs de frontend, API y PostgreSQL.
6. Consultar `/api/health` y `/api/metrics`.
7. Explicar que el volumen mantiene los datos aunque se detengan los contenedores.

Las credenciales presentes en Compose son intencionalmente locales y educativas. No deben reutilizarse en Producción.
