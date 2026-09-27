from __future__ import annotations

import math

import pytest
import torch

from the_well.research.metamorphosis.controller import (
    ControllerConfig,
    vorticity_weighted_damping_force,
)
from the_well.research.metamorphosis.metrics import enstrophy_balance_integrals
from the_well.research.metamorphosis.safety import (
    BoundaryMode,
    BoundaryState,
    OperationalMode,
    RiskVector,
    SafetyThresholds,
    ValidityGate,
    VerificationScales,
    VerificationState,
    configuration_fingerprint,
    detect_model_mismatch,
    evaluate_safety,
    minimum_flip_margin,
    minimum_recovery_cost,
    overpowering_metrics,
    risk_from_verification,
)


def test_validity_gate_requires_every_check() -> None:
    gate = ValidityGate(
        units_valid=True,
        domain_valid=True,
        inputs_complete=True,
        initial_conditions_valid=True,
        boundary_conditions_valid=False,
        identifiable=True,
    )
    assert not gate.passes
    assert gate.failures == ("boundary_conditions",)


def test_high_verification_risk_removes_control_authority() -> None:
    state = VerificationState(
        pde_residual=10.0,
        divergence_residual=0.0,
        energy_residual=0.0,
        solver_discrepancy=0.0,
        convergence_error=0.0,
        observation_mismatch=0.0,
        uncertainty=0.0,
        domain_distance=0.0,
    )
    scales = VerificationScales(
        pde_residual=1.0,
        divergence_residual=1.0,
        energy_residual=1.0,
        solver_discrepancy=1.0,
        convergence_error=1.0,
        observation_mismatch=1.0,
        uncertainty=1.0,
        domain_distance=1.0,
    )

    risk = risk_from_verification(state, scales)
    decision = evaluate_safety(risk)

    assert risk.physics > 0.9
    assert decision.mode is OperationalMode.ISOLATE
    assert decision.authority_scale == 0.0
    assert not decision.trusted_prediction


def test_model_mismatch_forces_at_least_safe_mode() -> None:
    risk = RiskVector(
        physics=0.0,
        numerical=0.0,
        uncertainty=0.0,
        control=0.0,
        external=0.0,
        mismatch=0.0,
    )
    decision = evaluate_safety(risk, model_mismatch=True)

    assert decision.mode is OperationalMode.SAFE
    assert decision.authority_scale < 1.0
    assert not decision.trusted_prediction
    assert "model_mismatch" in decision.reasons


def test_model_mismatch_detector_checks_observation_and_domain() -> None:
    state = VerificationState(
        pde_residual=0.0,
        divergence_residual=0.0,
        energy_residual=0.0,
        solver_discrepancy=0.0,
        convergence_error=0.0,
        observation_mismatch=2.0,
        uncertainty=0.0,
        domain_distance=0.0,
    )
    scales = VerificationScales(
        pde_residual=1.0,
        divergence_residual=1.0,
        energy_residual=1.0,
        solver_discrepancy=1.0,
        convergence_error=1.0,
        observation_mismatch=1.0,
        uncertainty=1.0,
        domain_distance=1.0,
    )
    assert detect_model_mismatch(state, scales, threshold=0.5)


def test_boundary_state_distinguishes_containment_and_environment_access() -> None:
    closed = BoundaryState(
        mode=BoundaryMode.CLOSED_STRONG,
        load=4.0,
        capacity=10.0,
        permeability=0.0,
        coupling=1.0,
        environmental_strength=100.0,
    )
    assert not closed.containment_failed
    assert closed.environmental_influence == 0.0
    assert closed.containment_margin == 6.0

    weak = BoundaryState(
        mode=BoundaryMode.WEAK_CONTAINMENT,
        load=12.0,
        capacity=10.0,
        permeability=0.5,
        coupling=0.4,
        environmental_strength=20.0,
    )
    assert weak.containment_failed
    assert weak.environmental_influence == pytest.approx(4.0)


def test_overpowering_event_tracks_strength_time_geometry_and_cascade() -> None:
    metrics = overpowering_metrics(
        disturbance=2.0,
        restoring=1.0,
        exceedance_duration=3.0,
        response_time=2.0,
        disturbance_time=1.0,
        concentration_factor=2.0,
        geometry_gain=1.5,
        coupling=0.5,
        cascade_gain=1.2,
        recoverability_distance=0.1,
    )
    assert metrics.effective_disturbance == pytest.approx(3.0)
    assert metrics.dominance_ratio == pytest.approx(3.0)
    assert metrics.accumulated_exceedance == pytest.approx(6.0)
    assert metrics.response_is_slower
    assert metrics.cascade_is_amplifying


def test_robustness_and_recovery_use_smallest_successful_perturbation() -> None:
    assert minimum_flip_margin(
        [0.5, 0.2, 0.8],
        [False, True, True],
    ) == pytest.approx(0.2)
    assert minimum_recovery_cost(
        [4.0, 2.0, 5.0],
        [False, True, True],
    ) == pytest.approx(2.0)
    assert math.isinf(minimum_flip_margin([0.1, 0.2], [False, False]))


def test_configuration_fingerprint_is_order_independent() -> None:
    left = {"viscosity": 0.001, "grid": [16, 16, 16]}
    right = {"grid": [16, 16, 16], "viscosity": 0.001}
    assert configuration_fingerprint(left) == configuration_fingerprint(right)


def test_safety_authority_can_zero_or_reduce_controller_output() -> None:
    velocity = torch.ones((4, 4, 2), dtype=torch.float64)
    omega = torch.full((4, 4), 5.0, dtype=torch.float64)
    config = ControllerConfig(
        safe_vorticity=1.0,
        proportional_gain=10.0,
        max_control_force=1.0,
    )

    full = vorticity_weighted_damping_force(
        velocity,
        omega,
        config,
        authority_scale=1.0,
    )
    restricted = vorticity_weighted_damping_force(
        velocity,
        omega,
        config,
        authority_scale=0.25,
    )
    isolated = vorticity_weighted_damping_force(
        velocity,
        omega,
        config,
        authority_scale=0.0,
    )

    full_max = torch.linalg.vector_norm(full, dim=-1).amax().item()
    restricted_max = torch.linalg.vector_norm(restricted, dim=-1).amax().item()
    assert full_max <= 1.0 + 1.0e-12
    assert restricted_max <= 0.25 + 1.0e-12
    assert torch.count_nonzero(isolated).item() == 0


def test_2d_enstrophy_balance_has_zero_stretching_production() -> None:
    grid_size = 64
    domain_length = 2.0 * math.pi
    step = domain_length / grid_size
    axis = torch.arange(grid_size, dtype=torch.float64) * step
    x, y = torch.meshgrid(axis, axis, indexing="ij")
    velocity = torch.stack(
        (
            torch.sin(x) * torch.cos(y),
            -torch.cos(x) * torch.sin(y),
        ),
        dim=-1,
    )

    total, production, dissipation = enstrophy_balance_integrals(
        velocity,
        (step, step),
        viscosity=1.0e-3,
    )

    assert total.item() > 0.0
    assert production.item() == 0.0
    assert dissipation.item() > 0.0


def test_thresholds_must_be_strictly_ordered() -> None:
    with pytest.raises(ValueError):
        SafetyThresholds(
            restricted=0.4,
            safe=0.3,
            emergency=0.7,
            isolate=0.9,
        ).validate()
