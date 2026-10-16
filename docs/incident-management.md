# Incident management

Lightweight process aligned with ITIL incident and problem management, sized for a small SRE team.

## Severity

| Sev | Definition | Example | Response | Updates |
|---|---|---|---|---|
| SEV1 | Members cannot use a core capability; data integrity or privacy at risk | Eligibility API down for all members | Page, IC + comms lead, exec notified | Every 30 min |
| SEV2 | Significant degradation or a subset of members affected | 10% of eligibility checks failing | Page, IC assigned | Every 60 min |
| SEV3 | Minor impact, workaround exists, or budget burning slowly | Slow-burn ticket, one non-critical endpoint slow | Ticket, business hours | Daily |

When in doubt, declare higher and downgrade later - it's cheaper than the reverse.

## Roles

- **Incident Commander (IC)** - owns coordination and decisions, not the keyboard. Default: whoever is on call.
- **Operations lead** - investigates and applies mitigations.
- **Communications lead** - status page / stakeholder updates (SEV1/SEV2).

## Lifecycle

1. **Detect** - SLO burn-rate alert, symptom alert, or a human report.
2. **Triage** - assign severity, open a channel, name the IC.
3. **Mitigate** - restore service first (rollback, failover, scale, disable feature). Root cause can wait.
4. **Resolve** - SLIs back within objective; alerts cleared.
5. **Learn** - blameless postmortem within 5 business days for SEV1/SEV2 and every `page`
   ([template](postmortem-template.md)). Action items become tracked tickets
   - this is where incident management hands off to **problem management**.

## On-call hygiene

- Every page must be actionable and link a runbook. A page that needed no action is a bug in the alert - fix or delete it.
- Track pages per shift; more than ~2 per on-call shift means toil is too high and reliability work gets prioritised.
- Handoff notes at the end of each rotation: open incidents, silenced alerts, risky upcoming changes.

## Regulated-environment notes

- Never paste member data (names, IDs, claims) into incident channels or tickets - use the `member_ref` pseudonym the service logs.
- If an incident may involve unauthorised access to member data, escalate to Security/Privacy immediately; breach-notification clocks may apply.
- Record timelines in UTC; postmortems are audit artefacts.
