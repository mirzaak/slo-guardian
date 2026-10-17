"""Prints how much error budget is left for each SLO.

Exits with code 1 if any budget is used up, so it can be used to block a deploy.

    python slo_report.py --prometheus http://localhost:9090 --window 1h
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

SLOS = [
    {
        "name": "availability",
        "objective": 0.995,
        "bad": 'sum(increase(http_requests_total{service="member-eligibility",status=~"5.."}[WINDOW]))',
        "total": 'sum(increase(http_requests_total{service="member-eligibility"}[WINDOW]))',
    },
    {
        "name": "latency",
        "objective": 0.95,
        "bad": 'sum(increase(http_request_duration_seconds_count{service="member-eligibility"}[WINDOW]))'
        ' - sum(increase(http_request_duration_seconds_bucket{service="member-eligibility",le="0.3"}[WINDOW]))',
        "total": 'sum(increase(http_request_duration_seconds_count{service="member-eligibility"}[WINDOW]))',
    },
]


def query(prometheus, promql):
    url = prometheus + "/api/v1/query?" + urllib.parse.urlencode({"query": promql})
    data = json.load(urllib.request.urlopen(url, timeout=10))
    result = data["data"]["result"]
    return float(result[0]["value"][1]) if result else 0.0


def error_budget(objective, bad, total):
    """Returns (sli, burn_rate, budget_left)."""
    if total == 0:
        return 1.0, 0.0, 1.0
    error_ratio = bad / total
    burn_rate = error_ratio / (1 - objective)
    return 1 - error_ratio, burn_rate, 1 - burn_rate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prometheus", default="http://localhost:9090")
    parser.add_argument("--window", default="30d")
    args = parser.parse_args()

    exhausted = False
    print(f"{'SLO':<14}{'TARGET':>8}{'SLI':>10}{'BURN':>8}{'BUDGET LEFT':>13}")
    for slo in SLOS:
        bad = query(args.prometheus, slo["bad"].replace("WINDOW", args.window))
        total = query(args.prometheus, slo["total"].replace("WINDOW", args.window))
        sli, burn, left = error_budget(slo["objective"], bad, total)
        print(f"{slo['name']:<14}{slo['objective']:>8.1%}{sli:>10.3%}{burn:>7.1f}x{left:>13.0%}")
        if left <= 0:
            exhausted = True

    if exhausted:
        print("\nError budget used up - don't deploy new features, fix reliability first.")
        sys.exit(1)


if __name__ == "__main__":
    main()
