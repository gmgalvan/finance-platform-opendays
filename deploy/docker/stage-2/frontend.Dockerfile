FROM nginx:1.27-alpine

COPY deploy/docker/stage-2/nginx.conf /etc/nginx/conf.d/default.conf
COPY app/stage-2/frontend/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -q --spider http://127.0.0.1/health/frontend || exit 1
