# Runbook: SLO error budget burn

Alerts: `MemberEligibilityAvailabilityFastBurn`, `MemberEligibilityAvailabilitySlowBurn`,
`MemberEligibilityLatencyFastBurn`, `MemberEligibilityLatencySlowBurn`

| Severity | Meaning | Response |
|---|---|---|
| `page` (fast burn) | ≥2% of the 30-day budget gone in 1h, or ≥5% in 6h | Acknowledge within 5 min, open an incident |
| `ticket` (slow burn) | On track to spend the whole budget before the period ends | Investigate during business hours |

## First 5 minutes

1. **Acknowledge** the page and post in the incident channel: *"Investigating member-eligibility &lt;slo&gt; burn, IC: &lt;you&gt;"*.
2. Open the **Member Eligibility - SLOs** Grafana dashboard.
3. Answer three questions before touching anything:
   - **Is it real?** Request rate by status - are 5xx/slow requests actually up, or did traffic drop to near zero?
   - **Is it everywhere?** Error ratio by route - one endpoint or all of them?
   - **What changed?** Recent deploys (`kubectl rollout history deploy/member-eligibility -n member-eligibility`), config changes, the *Fault injection* panel.

## availability

5xx responses on `/api/*`.

```bash
# Which pods are failing / restarting?
kubectl get pods -n member-eligibility -o wide
kubectl describe pod <pod> -n member-eligibility | tail -20

# Error logs (JSON - filter on status)
kubectl logs -n member-eligibility deploy/member-eligibility --since=15m | jq 'select(.status >= 500)'

# Is a game-day experiment still running?
curl -s http://<svc>/admin/chaos
```

**Mitigate first, debug second:**

| Likely cause | Mitigation |
|---|---|
| Bad deploy in the last hour | `kubectl rollout undo deploy/member-eligibility -n member-eligibility` |
| Fault injection left on | `curl -X DELETE http://<svc>/admin/chaos` |
| Pods OOMKilled / CrashLoopBackOff | Raise memory limit or roll back; check for a leak |
| Downstream dependency failing | Fail over / enable cached responses; engage owning team |
| Single bad node / AZ | `kubectl cordon <node>`; topology spread moves pods elsewhere |

## latency

Requests slower than 300ms on `/api/*`.

- **Saturation?** CPU throttling and HPA status: `kubectl get hpa -n member-eligibility`. If at `maxReplicas`, raise it and open a capacity-planning ticket.
- **One slow route?** Check *Latency percentiles* and *Error ratio by route*. A single slow route usually means a slow dependency.
- **Injected latency?** Check the *Fault injection* panel.

## Resolution

- The alert clears automatically once the short window recovers (5m/30m) - you do not need to wait for the 1h/6h windows.
- Post a resolution update, then file a postmortem using [the template](../postmortem-template.md) for any `page` incident.
- If the budget is exhausted, the release gate (`python -m slo.report --fail-on-exhausted`) will block feature deploys until it recovers - this is intended.
