from __future__ import annotations

import math

import pytest
import torch

from the_well.research.metamorphosis.controller import ControllerConfig
from the_well.research.metamorphosis.metrics import compute_metrics
from the_well.research.metamorphosis.run_3d_simulation import run_twin_experiment
from the_well.research.metamorphosis.safety import (
    BoundaryMode,
    BoundaryState,
    VerificationScales,
)
from the_well.research.metamorphosis.solver3d import (
    PeriodicSpectralNavierStokes3D,
    SpectralSimulationConfig,
)


def permissive_scales() -> VerificationScales:
    return VerificationScales(
        pde_residual=10.0,
        divergence_residual=1.0e-6,
        energy_residual=10.0,
        solver_discrepancy=10.0,
        convergence_error=1.0,
        observation_mismatch=10.0,
        uncertainty=10.0,
        domain_distance=10.0,
    )


def short_config(**overrides: object) -> SpectralSimulationConfig:
    values: dict[str, object] = {
        "grid_size": 8,
        "viscosity": 5.0e-2,
        "scalar_diffusivity": 1.0e-2,
        "time_step": 1.0e-3,
        "final_time": 2.0e-3,
        "verification_scales": permissive_scales(),
    }
    values.update(overrides)
    return SpectralSimulationConfig(**values)


def test_spectral_projection_enforces_incompressibility() -> None:
    solver = PeriodicSpectralNavierStokes3D(short_config())
    torch.manual_seed(7)
    velocity = torch.randn(
        (8, 8, 8, 3),
        dtype=torch.float64,
    )
    projected = solver.project_velocity_hat(solver._fft_vector(velocity))

    assert solver.divergence_linf_hat(projected) < 1.0e-10


def test_3d_taylor_green_has_nonzero_vortex_stretching() -> None:
    solver = PeriodicSpectralNavierStokes3D(short_config())
    velocity = solver.taylor_green_initial_velocity()
    metrics = compute_metrics(
        velocity,
        solver.spacing,
        viscosity=solver.config.viscosity,
    )

    assert metrics.vortex_stretching_rate > 0.0
    assert metrics.max_vorticity > 0.0


def test_unforced_viscous_run_loses_energy_and_preserves_scalar_mass() -> None:
    solver = PeriodicSpectralNavierStokes3D(short_config())
    _, records = solver.run()

    assert len(records) >= 1
    energies = [record.kinetic_energy for record in records]
    assert energies[-1] < energies[0]
    assert min(record.scalar_mass_fidelity for record in records) > 0.999999
    assert max(record.divergence_residual for record in records) < 1.0e-10


def test_live_observation_mismatch_reduces_authority_inside_solver() -> None:
    config = short_config(
        observation_mismatch=100.0,
        verification_scales=VerificationScales(
            pde_residual=10.0,
            divergence_residual=1.0e-6,
            energy_residual=10.0,
            solver_discrepancy=10.0,
            convergence_error=1.0,
            observation_mismatch=1.0,
            uncertainty=10.0,
            domain_distance=10.0,
        ),
    )
    solver = PeriodicSpectralNavierStokes3D(config)
    _, records = solver.run()

    first = records[0]
    assert first.model_mismatch
    assert not first.trusted_prediction
    assert first.authority_scale <= 0.25


def test_containment_failure_opens_environment_during_evolution() -> None:
    boundary = BoundaryState(
        mode=BoundaryMode.WEAK_CONTAINMENT,
        load=0.0,
        capacity=1.0e-3,
        permeability=0.2,
        coupling=0.5,
        environmental_strength=0.2,
    )
    solver = PeriodicSpectralNavierStokes3D(
        short_config(
            boundary=boundary,
            final_time=1.0e-3,
        )
    )
    _, records = solver.run()

    first = records[0]
    assert first.boundary_mode == BoundaryMode.OPEN.value
    assert first.containment_failed
    assert first.environmental_influence == pytest.approx(0.1)


def test_twin_run_uses_same_initial_problem_but_control_only_in_controlled_lane() -> None:
    config = short_config(
        final_time=1.0e-3,
        controller=ControllerConfig(
            safe_vorticity=0.1,
            proportional_gain=0.2,
            max_control_force=0.5,
        ),
    )
    result = run_twin_experiment(config)

    uncontrolled = result["uncontrolled"]
    controlled = result["controlled"]
    assert uncontrolled["maximum_control_effort"] == 0.0
    assert controlled["maximum_control_effort"] > 0.0
    assert math.isfinite(controlled["peak_vorticity"])
