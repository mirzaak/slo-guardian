import pytest
import yaml

from slo.budget import SLOStatus, load_config, render
from slo.generate_rules import OUTPUT, build, render_rules


def test_on_budget_burns_at_1x():
    s = SLOStatus("availability", 0.995, good=995, total=1000)
    assert s.burn_rate == pytest.approx(1.0)
    assert s.budget_remaining == pytest.approx(0.0)
    assert s.state == "EXHAUSTED"


def test_healthy_slo():
    s = SLOStatus("availability", 0.995, good=999, total=1000)
    assert s.sli == pytest.approx(0.999)
    assert s.budget_remaining == pytest.approx(0.8)
    assert s.state == "OK"


def test_at_risk():
    s = SLOStatus("latency", 0.95, good=961, total=1000)
    assert s.state == "AT RISK"


def test_no_traffic_is_compliant():
    s = SLOStatus("availability", 0.995, good=0, total=0)
    assert s.sli == 1.0
    assert s.state == "OK"


def test_render_keeps_promql_braces():
    assert render('x{a="b"}[{window}]', "5m") == 'x{a="b"}[5m]'


def test_invalid_objective_rejected(tmp_path):
    cfg = tmp_path / "slos.yaml"
    cfg.write_text(yaml.safe_dump({"service": "s", "period": "30d", "slos": [{"name": "x", "objective": 99.5}]}))
    with pytest.raises(ValueError):
        load_config(cfg)


def test_exactly_one_of_good_or_bad_query(tmp_path):
    cfg = tmp_path / "slos.yaml"
    slo = {"name": "x", "objective": 0.99, "total_query": "t", "good_query": "g", "bad_query": "b"}
    cfg.write_text(yaml.safe_dump({"service": "s", "period": "30d", "slos": [slo]}))
    with pytest.raises(ValueError):
        load_config(cfg)


def test_burn_rate_thresholds():
    rules = build(load_config())
    alerts = {r["alert"]: r for g in rules["groups"] for r in g.get("rules", []) if "alert" in r}
    fast = alerts["MemberEligibilityAvailabilityFastBurn"]
    assert fast["labels"]["severity"] == "page"
    assert "> 0.072" in fast["expr"]  # 14.4 * 0.5% budget


def test_committed_rules_are_up_to_date():
    assert OUTPUT.read_text() == render_rules(load_config()), "run `python -m slo.generate_rules`"
