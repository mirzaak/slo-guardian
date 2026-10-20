up:
	docker compose up -d --build

down:
	docker compose down

test:
	python -m pytest

test-rules:
	docker run --rm -v "$(CURDIR)/monitoring:/m" --entrypoint promtool prom/prometheus:v2.55.1 test rules /m/rules_test.yml

report:
	python slo_report.py --window 1h

chaos-on:
	curl -X PUT localhost:8000/chaos -H 'content-type: application/json' -d '{"error_rate": 0.2, "latency_ms": 250}'

chaos-off:
	curl -X PUT localhost:8000/chaos -H 'content-type: application/json' -d '{}'
