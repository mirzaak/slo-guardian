# Runbook

## AvailabilityBudgetBurn

Too many requests are failing with 5xx errors.

1. Open the Grafana dashboard. Check if errors are on one route or all of them.
2. Check if something changed recently:
   ```bash
   kubectl rollout history deployment/member-eligibility
   kubectl get pods
   kubectl logs deployment/member-eligibility --since=15m | grep " 5[0-9][0-9]$"
   ```
3. If a deploy caused it, roll back first and investigate after:
   ```bash
   kubectl rollout undo deployment/member-eligibility
   ```
4. Check that chaos testing wasn't left on (the "Injected error rate" panel).

## LatencyBudgetBurn

Too many requests are slower than 300ms.

1. Check the latency panel. Is it one route or everything?
2. Are pods out of CPU? `kubectl top pods`. If yes, scale up:
   `kubectl scale deployment/member-eligibility --replicas=5`
3. Check if latency was injected with chaos testing.

## ServiceDown

Prometheus can't scrape the app. Either the app is down or monitoring is broken.

1. `kubectl get pods` - are pods running?
2. `curl http://<service>/healthz`
3. If the app is up, check Prometheus -> Status -> Targets for the scrape error.

## After an incident

Write a short postmortem: what happened, impact, timeline, root cause, and action items.
Keep it blameless.
