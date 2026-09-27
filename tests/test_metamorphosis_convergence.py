from __future__ import annotations

from the_well.research.metamorphosis.convergence import (
    resolution_sweep,
    timestep_sweep,
)
from the_well.research.metamorphosis.safety import VerificationScales
from the_well.research.metamorphosis.solver3d import SpectralSimulationConfig


def base_config() -> SpectralSimulationConfig:
    return SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=5.0e-4,
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


def test_resolution_sweep_reports_pairwise_differences() -> None:
    points, differences = resolution_sweep(base_config(), [8, 10])

    assert len(points) == 2
    assert len(differences) == 1
    assert differences[0].kinetic_energy_relative_difference >= 0.0


def test_timestep_sweep_reports_pairwise_differences() -> None:
    config = base_config()
    points, differences = timestep_sweep(
        config,
        [5.0e-4, 2.5e-4],
    )

    assert len(points) == 2
    assert len(differences) == 1
    assert differences[0].vorticity_relative_difference >= 0.0
