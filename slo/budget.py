"""Error budget math, kept free of I/O so it is trivially testable."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).with_name("slos.yaml")
AT_RISK_THRESHOLD = 0.25  # flag SLOs with less than 25% of budget left


@dataclass(frozen=True)
class SLOStatus:
    name: str
    objective: float
    good: float
    total: float

    @property
    def sli(self) -> float:
        # No traffic means nothing failed: treat as fully compliant.
        if self.total <= 0 or math.isnan(self.total):
            return 1.0
        return min(max(self.good / self.total, 0.0), 1.0)

    @property
    def allowed_error_ratio(self) -> float:
        return 1.0 - self.objective

    @property
    def burn_rate(self) -> float:
        """How fast the budget is being consumed; 1.0 = exactly on budget."""
        return (1.0 - self.sli) / self.allowed_error_ratio

    @property
    def budget_remaining(self) -> float:
        """Fraction of the window's error budget left. Negative = overspent."""
        return 1.0 - self.burn_rate

    @property
    def state(self) -> str:
        if self.budget_remaining <= 0:
            return "EXHAUSTED"
        if self.budget_remaining < AT_RISK_THRESHOLD:
            return "AT RISK"
        return "OK"


def load_config(path: Path | str = DEFAULT_CONFIG) -> dict:
    with open(path) as fh:
        config = yaml.safe_load(fh)
    for slo in config["slos"]:
        if not 0 < slo["objective"] < 1:
            raise ValueError(f"SLO {slo['name']}: objective must be between 0 and 1")
        if ("good_query" in slo) == ("bad_query" in slo):
            raise ValueError(f"SLO {slo['name']}: define exactly one of good_query or bad_query")
    return config


def render(query: str, window: str) -> str:
    # str.format would choke on PromQL's own braces.
    return query.replace("{window}", window)
