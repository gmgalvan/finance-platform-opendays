.PHONY: demo-up demo-down obs-deploy obs-status k8s-traffic kind-up kind-down k8s-render k8s-deploy k8s-status k8s-smoke k8s-release k8s-rollback k8s-history k8s-watch k8s-ping test-setup test test-infra test-db-up test-db-down smoke serve-static serve-stage-2 stage-2-up stage-2-down stage-2-logs docker-build-static docker-run-static package-stage-3 terraform-stage-3-init terraform-stage-3-plan terraform-stage-3-apply terraform-stage-3-output terraform-stage-3-destroy

PYTHON ?= .venv/bin/python
TEST_DB_URL ?= postgresql://finance:finance_demo@localhost:55432/finance_platform

# --- Stage 5: pruebas -------------------------------------------------------

test-setup:
	uv venv --python 3.12 .venv
	uv pip install --python $(PYTHON) -r tests/requirements.txt

test:
	DATABASE_URL=$(TEST_DB_URL) $(PYTHON) -m pytest
	$(MAKE) test-infra

test-infra:
	terraform fmt -check -recursive infra/terraform
	terraform -chdir=infra/terraform/aws-ec2 init -backend=false -input=false >/dev/null
	terraform -chdir=infra/terraform/aws-ec2 validate

test-db-up:
	docker run --detach --rm --name finance-test-db \
		-e POSTGRES_DB=finance_platform -e POSTGRES_USER=finance -e POSTGRES_PASSWORD=finance_demo \
		-p 55432:5432 postgres:17-alpine
	until docker exec finance-test-db pg_isready -h 127.0.0.1 -U finance -d finance_platform >/dev/null 2>&1; do sleep 1; done

test-db-down:
	docker stop finance-test-db

smoke:
	tests/smoke/smoke.sh http://localhost:8082

# --- Stage 6: Kubernetes con Kind ------------------------------------------

KUSTOMIZE = kubectl kustomize --load-restrictor LoadRestrictionsNone deploy/kubernetes
# make k8s-deploy TAG=sha-<commit> despliega otra versión sin editar kustomization.yaml
TAG ?=
RENDER = $(KUSTOMIZE)$(if $(TAG), | sed -E 's|(ghcr.io/gmgalvan/finance-platform-[a-z-]+):sha-[0-9a-f]+|\1:$(TAG)|')

kind-up:
	kind create cluster --config deploy/kind/cluster.yaml --wait 120s

kind-down:
	kind delete cluster --name finance

k8s-render:
	$(RENDER)

k8s-deploy:
	$(RENDER) | kubectl apply -f -
	kubectl -n finance rollout status statefulset/postgres --timeout=180s
	kubectl -n finance rollout status deployment/api --timeout=180s
	kubectl -n finance rollout status deployment/frontend --timeout=180s
	kubectl -n finance rollout status deployment/market-data --timeout=180s

k8s-status:
	kubectl -n finance get pods,services,statefulsets,deployments -o wide

k8s-smoke:
	tests/smoke/smoke.sh http://localhost:8090

# Despliega la imagen del último commit de main (o TAG=sha-<commit>)
k8s-release:
	deploy/kind/release.sh $(TAG)

k8s-rollback:
	kubectl -n finance rollout undo deployment/api
	kubectl -n finance rollout undo deployment/frontend
	kubectl -n finance rollout undo deployment/market-data
	kubectl -n finance rollout status deployment/api --timeout=180s
	kubectl -n finance rollout status deployment/frontend --timeout=180s
	kubectl -n finance rollout status deployment/market-data --timeout=180s

k8s-history:
	kubectl -n finance rollout history deployment/frontend

# Para la demo: pods en vivo en una terminal y disponibilidad en otra
k8s-watch:
	kubectl -n finance get pods -l 'app.kubernetes.io/name in (api,frontend,market-data)' -w

k8s-ping:
	@while true; do \
		printf '%s  ' "$$(date +%T)"; \
		curl -s -o /dev/null -w 'HTTP %{http_code}  %{time_total}s\n' --max-time 2 http://localhost:8090/api/health || echo 'sin respuesta'; \
		sleep 0.5; \
	done

k8s-traffic:
	deploy/kind/traffic.sh http://localhost:8090

# --- Stage 8: observabilidad -------------------------------------------------

obs-deploy:
	kubectl apply -k observability
	kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
	kubectl -n monitoring rollout status deployment/grafana --timeout=180s
	@echo "Grafana:    http://localhost:3000  (anónimo de solo lectura; admin / opendays)"
	@echo "Prometheus: http://localhost:9090/targets"
	@echo "Jaeger:     http://localhost:16686"

obs-status:
	kubectl -n monitoring get pods,services

# --- Todo junto, para el día de la charla ------------------------------------

demo-up: kind-up k8s-deploy obs-deploy k8s-smoke
	@echo
	@echo "App:        http://localhost:8090"
	@echo "Grafana:    http://localhost:3000"
	@echo "Prometheus: http://localhost:9090"
	@echo "Jaeger:     http://localhost:16686"

demo-down: kind-down

# --- Stages 1-3 --------------------------------------------------------------

serve-static:
	python3 -m http.server 8080 --directory app/frontend

serve-stage-2:
	python3 -m http.server 8081 --directory app/stage-2/frontend

stage-2-up:
	docker compose -f deploy/compose/stage-2/compose.yaml up --build --detach

stage-2-down:
	docker compose -f deploy/compose/stage-2/compose.yaml down

stage-2-logs:
	docker compose -f deploy/compose/stage-2/compose.yaml logs --follow

package-stage-3:
	mkdir -p infra/terraform/aws-ec2/build
	tar -czf infra/terraform/aws-ec2/build/finance-platform-stage-3.tar.gz app/stage-2 deploy/docker/stage-2

terraform-stage-3-init:
	terraform -chdir=infra/terraform/aws-ec2 init

terraform-stage-3-plan: package-stage-3
	terraform -chdir=infra/terraform/aws-ec2 plan -out=stage-3.tfplan

terraform-stage-3-apply:
	terraform -chdir=infra/terraform/aws-ec2 apply stage-3.tfplan

terraform-stage-3-output:
	terraform -chdir=infra/terraform/aws-ec2 output

terraform-stage-3-destroy:
	terraform -chdir=infra/terraform/aws-ec2 destroy

docker-build-static:
	docker build -f deploy/docker/stage-1/Dockerfile -t finance-journal:stage-1 .

docker-run-static:
	docker run --rm -p 8080:80 --name finance-journal-stage-1 finance-journal:stage-1
