import asyncio
import hashlib
import logging
import os
import random
import time

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

SERVICE = "member-eligibility"
PLANS = ["PPO-GOLD", "HMO-SILVER", "HDHP-BRONZE"]

REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "route", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "route"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 1, 2.5, 5),
)
CHAOS_ERROR_RATE = Gauge("chaos_error_rate", "Injected error rate", ["service"])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(SERVICE)

app = FastAPI(title="Member Eligibility API")


class Chaos(BaseModel):
    error_rate: float = Field(0, ge=0, le=1)
    latency_ms: int = Field(0, ge=0, le=10000)


chaos = Chaos()


@app.middleware("http")
async def track_requests(request: Request, call_next):
    # only API calls count towards the SLOs (not /healthz or /metrics)
    if not request.url.path.startswith("/api"):
        return await call_next(request)

    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # label by route template, not the real path, so member ids never end up in metrics
        route = request.scope.get("route")
        route = route.path if route else "unknown"
        REQUESTS.labels(SERVICE, route, str(status)).inc()
        LATENCY.labels(SERVICE, route).observe(time.perf_counter() - start)
        log.info("%s %s %s", request.method, route, status)


async def maybe_fail():
    if chaos.latency_ms:
        await asyncio.sleep(chaos.latency_ms / 1000)
    if random.random() < chaos.error_rate:
        raise HTTPException(503, "injected failure")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/plans")
async def plans():
    await maybe_fail()
    return {"plans": PLANS}


@app.get("/api/v1/members/{member_id}/eligibility")
async def eligibility(member_id: str):
    await maybe_fail()
    if not (member_id.startswith("M") and member_id[1:].isdigit()):
        raise HTTPException(404, "member not found")

    await asyncio.sleep(random.uniform(0.005, 0.04))  # pretend to call a database
    number = int(hashlib.sha256(member_id.encode()).hexdigest(), 16)
    return {"plan": PLANS[number % len(PLANS)], "active": number % 10 != 0}


@app.put("/chaos")
def set_chaos(new: Chaos):
    if os.getenv("CHAOS_ENABLED") != "true":
        raise HTTPException(404)
    global chaos
    chaos = new
    CHAOS_ERROR_RATE.labels(SERVICE).set(new.error_rate)
    log.warning("chaos set to %s", new)
    return chaos
