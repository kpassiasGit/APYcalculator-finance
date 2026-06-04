"""Unit tests for APY projections (no network required)."""

import math

from finlytics.apy import project_apy


def test_zero_growth_returns_principal():
    result = project_apy(1000, 0.0, years=1.0)
    assert math.isclose(result.final_value, 1000, rel_tol=1e-9)
    assert math.isclose(result.profit, 0.0, abs_tol=1e-9)


def test_daily_compounding_beats_simple_interest():
    # 5% APY daily-compounded for a year should exceed flat 5%.
    result = project_apy(1000, 5.0, years=1.0, compounding_per_year=365)
    assert result.final_value > 1050.0
    assert result.final_value < 1052.0  # but only slightly (continuous ~ 1051.27)


def test_monthly_contributions_are_tracked():
    result = project_apy(
        0.0, 0.0, years=1.0, compounding_per_year=12, monthly_contribution=100
    )
    # 11 contributions land after period 0 over 12 monthly periods.
    assert math.isclose(result.contributions, 1100, abs_tol=1e-6)
    assert math.isclose(result.final_value, 1100, abs_tol=1e-6)


def test_negative_inputs_rejected():
    try:
        project_apy(-100, 5.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for negative principal")
