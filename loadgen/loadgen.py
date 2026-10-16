"""Tiny stdlib-only traffic generator so the dashboards have something to show.

    python -m loadgen.loadgen --target http://localhost:8000 --workers 4 --rps 5
"""

from __future__ import annotations

import argparse
import random
import threading
import time
import urllib.error
import urllib.request


def pick_path() -> str:
    r = random.random()
    if r < 0.80:
        return f"/api/v1/members/M{random.randint(0, 999_999):06d}/eligibility"
    if r < 0.95:
        return "/api/v1/plans"
    return "/api/v1/members/not-a-member/eligibility"  # 404s: client errors, not SLO violations


def worker(target: str, rps: float, stop: threading.Event) -> None:
    interval = 1.0 / rps
    while not stop.is_set():
        try:
            urllib.request.urlopen(target + pick_path(), timeout=15).read()
        except urllib.error.HTTPError:
            pass  # 4xx/5xx are expected; the service's own metrics record them
        except OSError as exc:
            print(f"loadgen: {target} unreachable ({exc}); retrying", flush=True)
            time.sleep(2)
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="http://localhost:8000")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rps", type=float, default=5, help="requests per second, per worker")
    args = parser.parse_args()

    stop = threading.Event()
    threads = [
        threading.Thread(target=worker, args=(args.target.rstrip("/"), args.rps, stop), daemon=True)
        for _ in range(args.workers)
    ]
    for t in threads:
        t.start()
    print(f"loadgen: {args.workers} workers x {args.rps} rps -> {args.target}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
