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

## AvailabilityBudgetSlowBurn

Severity `ticket`, not a page. Errors are low but steady: at this rate the 30-day budget is gone in
about 10 days. Handle it during working hours.

1. Run `python slo_report.py --window 1d` to see the burn rate over the last day.
2. Look for a route or dependency that fails a little all the time (same checks as AvailabilityBudgetBurn).
3. If it keeps burning, stop feature deploys until it's fixed.

## LatencyBudgetBurn

Too many requests are slower than 300ms.

1. Check the latency panel. Is it one route or everything?
2. Are pods out of CPU? `kubectl top pods`. The HPA should add pods on its own - check it with
   `kubectl get hpa member-eligibility`. If it's already at max replicas, raise `maxReplicas`
   in `k8s/hpa.yaml` (`kubectl scale` won't help, the HPA overrides it).
3. Check if latency was injected with chaos testing.

## LatencyBudgetSlowBurn

Severity `ticket`, not a page. A steady share of requests is slower than 300ms: at this rate the
30-day budget is gone in about 10 days. Handle it during working hours.

1. Check the latency panel for a route that got slower over the last day or two.
2. Compare with recent deploys (`kubectl rollout history deployment/member-eligibility`).
3. Check `kubectl get hpa member-eligibility` - if it sits at max replicas, the service needs more capacity.

## ServiceDown

Prometheus can't scrape the app. Either the app is down or monitoring is broken.

1. `kubectl get pods` - are pods running?
2. `curl http://<service>/healthz`
3. If the app is up, check Prometheus -> Status -> Targets for the scrape error.

## After an incident

Write a short postmortem: what happened, impact, timeline, root cause, and action items.
Keep it blameless.
