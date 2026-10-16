# Runbook: Target down

Alert: `MemberEligibilityTargetDown` (page)

Prometheus has not scraped the service for 2 minutes. Either the service is down
(**users impacted**) or monitoring is broken (**we are blind** - SLO alerts can't fire).

1. Is the service actually serving?
   ```bash
   kubectl get pods,endpoints -n member-eligibility
   curl -s -o /dev/null -w '%{http_code}\n' http://<svc>/readyz
   ```
2. **Service down** -> treat as a SEV1/SEV2 availability incident; follow the
   availability section of the [burn-rate runbook](slo-burn-rate.md#availability).
3. **Service up, scrape failing** -> check Prometheus *Status -> Targets* for the
   scrape error (network policy, wrong port, `/metrics` returning 5xx). Fixing this
   is urgent but user impact is nil; downgrade to SEV3 once confirmed.
