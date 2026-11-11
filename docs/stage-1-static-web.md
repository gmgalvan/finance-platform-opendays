# Stage 1: static web

Esta etapa representa la primera versión de Finance Journal: una publicación financiera construida únicamente con HTML y CSS y servida desde una máquina Linux.

El diseño reproduce convenciones comunes de la Web de finales de los años noventa: página optimizada para 800 × 600, fondo gris, botones con relieve, enlaces azules, contador de visitas ilustrativo y distintivos de compatibilidad. Mantiene HTML semántico y adaptación móvil para que la demostración siga siendo accesible en navegadores actuales.

## Noticias históricas incluidas

- Recorte de tasas de la Reserva Federal del 15 de octubre de 1998.
- Crisis financiera rusa de 1998.
- Recapitalización de Long-Term Capital Management en septiembre de 1998.

Cada noticia enlaza una fuente histórica de la Reserva Federal o del Fondo Monetario Internacional. Los valores de la tabla de mercados permanecen marcados como datos ilustrativos.

## Ejecutar sin contenedores

```bash
make serve-static
```

Abrir `http://localhost:8080`.

## Ejecutar con Nginx en Docker

```bash
make docker-build-static
make docker-run-static
```

Abrir `http://localhost:8080`. El endpoint `http://localhost:8080/health` devuelve `ok` cuando Nginx está disponible.

## Qué mostrar durante la charla

1. El navegador solicita archivos HTML y CSS a un único servidor.
2. No existen API, base de datos, cuentas ni pagos.
3. Cada cambio requiere modificar y volver a publicar los archivos.
4. Nginx registra solicitudes, errores y tiempo de respuesta.
5. Linux permite observar CPU, memoria y disco con `top`, `free` y `df`.

## Comandos de observabilidad básica

Con el contenedor en ejecución:

```bash
docker logs finance-journal-stage-1
docker stats finance-journal-stage-1
curl http://localhost:8080/health
```

Esta observabilidad es reactiva y está ligada a una sola máquina. Esa limitación prepara la transición hacia la aplicación de tres capas y herramientas de monitoreo centralizadas.
