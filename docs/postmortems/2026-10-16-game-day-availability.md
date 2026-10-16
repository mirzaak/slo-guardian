# Postmortem: Game day - injected 20% error rate on eligibility API

| | |
|---|---|
| **Date** | 2026-10-16 |
| **Severity** | SEV2 (simulated) |
| **Duration** | ~4 min from injection to page |
| **Status** | Reviewed |

*This is a planned game-day exercise, written up with the real postmortem template to validate the detection pipeline end to end.*

## Summary
Fault injection (`PUT /admin/chaos {"error_rate":0.2,"latency_ms":250}`) made 20% of
API requests return 503 and added 250ms to every request. The availability fast-burn
alert paged; the latency SLO correctly did **not** page.

## Impact
- ~20% of `/api/*` requests failed for the duration of the exercise (local environment, synthetic traffic).
- Availability burn rate peaked at ~22x (page threshold 14.4x).
- p95 latency rose to ~290ms - just under the 300ms threshold - so the latency SLO burned at only ~0.06x.

## Timeline
| T+ | Event |
|---|---|
| 0:00 | Fault injection enabled |
| ~2:00 | 1h availability burn rate crosses 14.4x (5m window already above) |
| ~4:00 | `MemberEligibilityAvailabilityFastBurn` fires after its 2m `for` and routes to the `page` receiver |
| ~4:00 | `python -m slo.report --fail-on-exhausted` exits 2 - release gate closed |
| — | `MemberEligibilityAvailabilitySlowBurn` inhibited by the page (no duplicate ticket) |
| ~5:00 | `DELETE /admin/chaos`; error ratio returns to 0 and the alert resolves once the 5m window recovers |

## What went well
- Multi-window alert fired within minutes of a real budget-threatening error rate.
- Inhibition prevented the slow-burn ticket from duplicating the page.
- The dashboard made the cause obvious within seconds (*Fault injection* panel).

## What went poorly / lucky
- 250ms of added latency landed just under the 300ms threshold: a slightly slower downstream would have pushed most requests over it. The latency SLO has little headroom when a dependency degrades.

## Action items
| Action | Type | Owner |
|---|---|---|
| Add a ticket-severity alert on p95 > 250ms sustained for 30m as an early warning | detect | SRE |
| Add the `MemberEligibilityChaosActive` alert so experiments can't be left on | detect | SRE - done |
