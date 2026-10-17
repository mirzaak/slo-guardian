from pytest import approx

from slo_report import error_budget


def test_no_errors():
    assert error_budget(0.995, bad=0, total=1000) == (1.0, 0.0, 1.0)


def test_half_budget_used():
    sli, burn, left = error_budget(0.995, bad=25, total=10000)
    assert sli == approx(0.9975)
    assert burn == approx(0.5)
    assert left == approx(0.5)


def test_budget_used_up():
    _, burn, left = error_budget(0.995, bad=10, total=1000)
    assert burn == approx(2)
    assert left < 0


def test_no_traffic():
    assert error_budget(0.95, bad=0, total=0) == (1.0, 0.0, 1.0)
