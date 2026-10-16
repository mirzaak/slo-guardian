.PHONY: install up down test lint rules check-rules test-rules validate-k8s report chaos-on chaos-off

PY ?= .venv/bin/python
PROM_IMAGE = prom/prometheus:v2.55.1

install:            ## create venv and install dev deps
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

up:                 ## start app + loadgen + Prometheus + Alertmanager + Grafana
	docker compose up -d --build

down:
	docker compose down

test:               ## unit tests
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

rules:              ## regenerate Prometheus rules from slo/slos.yaml
	$(PY) -m slo.generate_rules

check-rules:        ## promtool: validate config + run alert unit tests
	$(PY) -m slo.generate_rules --check
	docker run --rm -v "$(PWD)/monitoring:/m:ro" --entrypoint promtool $(PROM_IMAGE) check config /m/prometheus.yml
	docker run --rm -v "$(PWD)/monitoring:/m:ro" --entrypoint promtool $(PROM_IMAGE) test rules /m/tests/slo-alerts.test.yml

validate-k8s:       ## render kustomize and validate against k8s schemas
	kubectl kustomize k8s/base | docker run --rm -i ghcr.io/yannh/kubeconform:latest -strict -summary -

report:             ## error budget report for the last hour
	$(PY) -m slo.report --window 1h

chaos-on:           ## game day: 20% errors + 250ms latency
	curl -s -X PUT localhost:8000/admin/chaos -H 'content-type: application/json' -d '{"error_rate":0.2,"latency_ms":250}'

chaos-off:
	curl -s -X DELETE localhost:8000/admin/chaos
