from __future__ import annotations

from the_well.research.metamorphosis.run_3d_verification import (
    run_verification_battery,
)
from the_well.research.metamorphosis.safety import VerificationScales
from the_well.research.metamorphosis.solver3d import SpectralSimulationConfig


def test_complete_3d_verification_battery_smoke() -> None:
    config = SpectralSimulationConfig(
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

    result = run_verification_battery(
        config,
        grid_sizes=(8, 10),
        time_steps=(5.0e-4, 2.5e-4),
        amplitude_perturbations=(0.01,),
    )

    assert result["twin_experiment"]["uncontrolled"]["steps"] > 0
    assert len(result["resolution_sweep"]["points"]) == 2
    assert len(result["timestep_sweep"]["points"]) == 2
    assert len(result["amplitude_robustness"]["points"]) == 1
