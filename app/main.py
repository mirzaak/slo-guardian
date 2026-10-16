"""Member Eligibility API.

A small, synthetic healthcare-style service used to demonstrate SRE practices:
RED metrics with bounded label cardinality, liveness/readiness probes,
structured logs that never contain member identifiers, and controlled fault
injection for game days. All data is generated - there is no PHI anywhere.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import time
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

SERVICE = "member-eligibility"
VERSION = os.getenv("APP_VERSION", "dev")
MEMBER_ID = re.compile(r"^M\d{6}$")
# Probe and scrape traffic is excluded so it can't inflate the SLIs.
UNINSTRUMENTED = {"/metrics", "/healthz", "/readyz"}

REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests.", ["service", "route", "method", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["service", "route", "method"],
    # 0.3 is the latency SLO threshold, so it must be an exact bucket boundary.
    buckets=(0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_FLIGHT = Gauge("http_requests_in_flight", "In-flight HTTP requests.", ["service"])
CHAOS_ERROR_RATE = Gauge("chaos_error_rate", "Injected error probability (0-1).", ["service"])
CHAOS_LATENCY = Gauge("chaos_latency_seconds", "Injected extra latency in seconds.", ["service"])
BUILD_INFO = Gauge("app_build_info", "Build metadata.", ["service", "version"])
BUILD_INFO.labels(SERVICE, VERSION).set(1)

PLANS = [
    {"id": "PPO-GOLD", "name": "PPO Gold", "network": "national"},
    {"id": "HMO-SILVER", "name": "HMO Silver", "network": "regional"},
    {"id": "HDHP-BRONZE", "name": "HDHP Bronze + HSA", "network": "national"},
]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": SERVICE,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload)


log = logging.getLogger(SERVICE)
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
log.addHandler(_handler)
log.setLevel(os.getenv("LOG_LEVEL", "INFO"))
log.propagate = False


class ChaosConfig(BaseModel):
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Probability of returning 503")
    latency_ms: int = Field(0, ge=0, le=10_000, description="Extra latency added to API calls")


state: dict = {"ready": False, "chaos": ChaosConfig()}


def chaos_enabled() -> bool:
    return os.getenv("CHAOS_ENABLED", "false").lower() == "true"


def set_chaos(config: ChaosConfig) -> None:
    state["chaos"] = config
    CHAOS_ERROR_RATE.labels(SERVICE).set(config.error_rate)
    CHAOS_LATENCY.labels(SERVICE).set(config.latency_ms / 1000)


def member_ref(member_id: str) -> str:
    """Stable pseudonymous reference so responses and logs never echo the raw ID."""
    return hashlib.sha256(member_id.encode()).hexdigest()[:12]


@asynccontextmanager
async def lifespan(_: FastAPI):
    set_chaos(ChaosConfig())
    state["ready"] = True
    log.info("startup", extra={"fields": {"version": VERSION, "chaos_enabled": chaos_enabled()}})
    yield
    # Fail readiness first so the load balancer drains us before shutdown.
    state["ready"] = False
    log.info("shutdown")


app = FastAPI(title="Member Eligibility API", version=VERSION, lifespan=lifespan)


@app.middleware("http")
async def observe(request: Request, call_next):
    if request.url.path in UNINSTRUMENTED:
        return await call_next(request)

    start = time.perf_counter()
    IN_FLIGHT.labels(SERVICE).inc()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        # Label by route template, never the raw path: keeps cardinality bounded
        # and keeps member IDs out of metrics and logs.
        route = request.scope.get("route")
        route_label = route.path if route else "unmatched"
        REQUESTS.labels(SERVICE, route_label, request.method, str(status)).inc()
        LATENCY.labels(SERVICE, route_label, request.method).observe(elapsed)
        IN_FLIGHT.labels(SERVICE).dec()
        log.info(
            "request",
            extra={
                "fields": {
                    "route": route_label,
                    "method": request.method,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 2),
                }
            },
        )


async def inject_faults() -> None:
    chaos: ChaosConfig = state["chaos"]
    if chaos.latency_ms:
        await asyncio.sleep(chaos.latency_ms / 1000)
    if chaos.error_rate and random.random() < chaos.error_rate:
        raise HTTPException(status_code=503, detail="injected fault")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    if not state["ready"]:
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/plans")
async def list_plans():
    await inject_faults()
    return {"plans": PLANS}


@app.get("/api/v1/members/{member_id}/eligibility")
async def eligibility(member_id: str):
    await inject_faults()
    if not MEMBER_ID.match(member_id):
        raise HTTPException(status_code=404, detail="member not found")

    # Simulated downstream lookup (claims/eligibility system of record).
    await asyncio.sleep(random.uniform(0.005, 0.04))

    digest = int(hashlib.sha256(member_id.encode()).hexdigest(), 16)
    plan = PLANS[digest % len(PLANS)]
    active = digest % 10 != 0
    return {
        "member_ref": member_ref(member_id),
        "plan_id": plan["id"],
        "status": "active" if active else "inactive",
        "coverage_end": (date.today() + timedelta(days=digest % 365)).isoformat() if active else None,
    }


@app.get("/admin/chaos", include_in_schema=False)
async def get_chaos():
    if not chaos_enabled():
        raise HTTPException(status_code=404)
    return state["chaos"]


@app.put("/admin/chaos", include_in_schema=False)
async def put_chaos(config: ChaosConfig):
    if not chaos_enabled():
        raise HTTPException(status_code=404)
    set_chaos(config)
    log.warning("chaos_updated", extra={"fields": config.model_dump()})
    return config


@app.delete("/admin/chaos", include_in_schema=False)
async def reset_chaos():
    if not chaos_enabled():
        raise HTTPException(status_code=404)
    set_chaos(ChaosConfig())
    log.warning("chaos_reset")
    return state["chaos"]
