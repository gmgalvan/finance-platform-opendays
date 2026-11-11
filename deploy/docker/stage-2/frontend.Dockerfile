# Variante oficial de Nginx que incluye el módulo de OpenTelemetry.
FROM nginx:1.27-alpine-otel

# El módulo viene incluido pero no cargado.
RUN sed -i '1i load_module modules/ngx_otel_module.so;' /etc/nginx/nginx.conf

# Valores por defecto: sin trazas (Docker Compose, CI, EC2).
# Kubernetes los cambia para enviar trazas a Jaeger.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    OTEL_TRACE=off \
    OTEL_EXPORTER_ENDPOINT=localhost:4317 \
    OTLP_HTTP_COLLECTOR=http://127.0.0.1:4318

COPY deploy/docker/stage-2/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY app/stage-2/frontend/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -q --spider http://127.0.0.1/health/frontend || exit 1
