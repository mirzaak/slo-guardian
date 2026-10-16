"""Error budget report and deploy gate.

    python -m slo.report --prometheus http://localhost:9090 --window 1h
    python -m slo.report --fail-on-exhausted   # exit 2 if any budget is spent

Use --fail-on-exhausted in a pipeline before promoting a release: if the
service has already burned its error budget, ship reliability fixes, not features.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

from slo.budget import DEFAULT_CONFIG, SLOStatus, load_config, render


def query_scalar(prometheus_url: str, promql: str) -> float:
    url = f"{prometheus_url.rstrip('/')}/api/v1/query?{urlencode({'query': promql})}"
    with urlopen(url, timeout=15) as resp:
        body = json.load(resp)
    if body.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {body}")
    result = body["data"]["result"]
    if not result:
        return 0.0
    value = float(result[0]["value"][1])
    return 0.0 if math.isnan(value) else value


def collect(config: dict, prometheus_url: str, window: str) -> list[SLOStatus]:
    statuses = []
    for slo in config["slos"]:
        total = query_scalar(prometheus_url, render(slo["total_query"], window))
        if "bad_query" in slo:
            good = total - query_scalar(prometheus_url, render(slo["bad_query"], window))
        else:
            good = query_scalar(prometheus_url, render(slo["good_query"], window))
        statuses.append(SLOStatus(name=slo["name"], objective=slo["objective"], good=good, total=total))
    return statuses


def print_table(service: str, window: str, statuses: list[SLOStatus]) -> None:
    print(f"\nSLO report - {service} (window {window})\n")
    header = f"{'SLO':<14}{'OBJECTIVE':>10}{'SLI':>10}{'BUDGET LEFT':>13}{'BURN':>8}{'EVENTS':>10}  STATE"
    print(header)
    print("-" * len(header))
    for s in statuses:
        print(
            f"{s.name:<14}{s.objective:>10.2%}{s.sli:>10.3%}{s.budget_remaining:>13.1%}"
            f"{s.burn_rate:>7.2f}x{int(s.total):>10,}  {s.state}"
        )
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prometheus", default=os.getenv("PROMETHEUS_URL", "http://localhost:9090"))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--window", help="PromQL range; defaults to the SLO period in the config")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--fail-on-exhausted", action="store_true", help="exit 2 if any budget is spent")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    window = args.window or config["period"]
    statuses = collect(config, args.prometheus, window)

    if args.json:
        print(json.dumps([
            {
                "slo": s.name,
                "objective": s.objective,
                "sli": s.sli,
                "budget_remaining": s.budget_remaining,
                "burn_rate": s.burn_rate,
                "events": s.total,
                "state": s.state,
            }
            for s in statuses
        ], indent=2))
    else:
        print_table(config["service"], window, statuses)

    if args.fail_on_exhausted and any(s.state == "EXHAUSTED" for s in statuses):
        print("Error budget exhausted - blocking release.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
