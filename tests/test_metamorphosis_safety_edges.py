from __future__ import annotations

import math

import pytest

from the_well.research.metamorphosis.safety import (
    BoundaryMode,
    BoundaryState,
    minimum_recovery_cost,
    overpowering_metrics,
)


def test_zero_restoring_capacity_reports_infinite_dominance() -> None:
    metrics = overpowering_metrics(
        disturbance=1.0,
        restoring=0.0,
        exceedance_duration=1.0,
        response_time=1.0,
        disturbance_time=1.0,
    )
    assert math.isinf(metrics.dominance_ratio)
    assert math.isinf(metrics.accumulated_exceedance)


def test_zero_duration_with_zero_restoring_does_not_create_nan() -> None:
    metrics = overpowering_metrics(
        disturbance=1.0,
        restoring=0.0,
        exceedance_duration=0.0,
        response_time=1.0,
        disturbance_time=1.0,
    )
    assert metrics.accumulated_exceedance == 0.0


def test_closed_boundary_rejects_nonzero_permeability() -> None:
    with pytest.raises(ValueError, match="zero permeability"):
        BoundaryState(
            mode=BoundaryMode.CLOSED_STRONG,
            load=1.0,
            capacity=2.0,
            permeability=0.1,
            coupling=1.0,
            environmental_strength=1.0,
        )


def test_missing_recovery_returns_infinite_cost() -> None:
    assert math.isinf(minimum_recovery_cost([1.0, 2.0], [False, False]))
