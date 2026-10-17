"""Sends random traffic to the API so the dashboard has something to show."""
import random
import sys
import time
import urllib.request

target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

while True:
    member = f"M{random.randint(0, 999999):06d}"
    path = random.choice([
        f"/api/v1/members/{member}/eligibility",
        f"/api/v1/members/{member}/eligibility",
        f"/api/v1/members/{member}/eligibility",
        "/api/v1/plans",
        "/api/v1/members/unknown/eligibility",  # 404, should not count as an error
    ])
    try:
        urllib.request.urlopen(target + path, timeout=15)
    except Exception:
        pass
    time.sleep(0.05)
