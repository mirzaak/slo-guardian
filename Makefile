up:
	docker compose up -d --build

down:
	docker compose down

test:
	python -m pytest

report:
	python slo_report.py --window 1h

chaos-on:
	curl -X PUT localhost:8000/chaos -H 'content-type: application/json' -d '{"error_rate": 0.2, "latency_ms": 250}'

chaos-off:
	curl -X PUT localhost:8000/chaos -H 'content-type: application/json' -d '{}'
