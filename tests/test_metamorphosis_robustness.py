from __future__ import annotations

import math

from the_well.research.metamorphosis.controller import ControllerConfig
from the_well.research.metamorphosis.robustness import (
    amplitude_robustness_sweep,
    recovery_sweep,
)
from the_well.research.metamorphosis.safety import VerificationScales
from the_well.research.metamorphosis.solver3d import SpectralSimulationConfig


def config() -> SpectralSimulationConfig:
    return SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=5.0e-4,
        controller=ControllerConfig(
            safe_vorticity=0.1,
            proportional_gain=0.01,
            max_control_force=1.0,
        ),
        verification_scales=VerificationScales(
            pde_residual=10.0,
            divergence_residual=1.0e-6,
            energy_residual=10.0,
            solver_discrepancy=10.0,
            convergence_error=1.0,
            observation_mismatch=10.0,
            uncertainty=10.0,
            domain_distance=10.0,
        ),
    )


def test_amplitude_robustness_reports_no_flip_when_tested_cases_match() -> None:
    results, margin = amplitude_robustness_sweep(
        config(),
        [0.0, 0.01],
    )

    assert len(results) == 2
    assert math.isinf(margin)


def test_recovery_sweep_returns_measured_control_cost() -> None:
    trials, minimum_cost = recovery_sweep(
        config(),
        [0.1, 0.2],
        max_velocity_gradient_limit=100.0,
    )

    assert len(trials) == 2
    assert minimum_cost >= 0.0
    assert any(trial.recovered for trial in trials)
