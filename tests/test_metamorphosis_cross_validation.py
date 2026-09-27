from __future__ import annotations

from dataclasses import replace

from the_well.research.metamorphosis.cross_validation import (
    compare_uncontrolled_solvers,
)
from the_well.research.metamorphosis.safety import VerificationScales
from the_well.research.metamorphosis.solver3d import SpectralSimulationConfig
from the_well.research.metamorphosis.solver_fd3d import (
    PeriodicFiniteDifferenceNavierStokes3D,
)


def crosscheck_config() -> SpectralSimulationConfig:
    return SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=1.0e-3,
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


def test_finite_difference_baseline_dissipates_energy() -> None:
    solver = PeriodicFiniteDifferenceNavierStokes3D(crosscheck_config())
    initial = solver.project(solver.taylor_green_initial_velocity())
    initial_energy = solver.kinetic_energy(initial)

    final, records = solver.run()

    assert records
    assert records[-1].kinetic_energy < initial_energy
    assert solver.kinetic_energy(final) == records[-1].kinetic_energy
    assert records[-1].divergence_residual < 1.0e-8


def test_spectral_and_finite_difference_paths_agree_over_short_horizon() -> None:
    comparison = compare_uncontrolled_solvers(crosscheck_config())

    assert comparison.spectral_steps > 0
    assert comparison.finite_difference_steps > 0
    assert comparison.velocity_relative_l2 < 0.20
    assert comparison.kinetic_energy_relative_error < 0.10
    assert comparison.max_vorticity_relative_error < 0.20


def test_crosscheck_rejects_environment_forcing() -> None:
    config = crosscheck_config()
    forced_boundary = replace(
        config.boundary,
        environmental_strength=1.0,
    )
    forced = replace(config, boundary=forced_boundary)

    try:
        compare_uncontrolled_solvers(forced)
    except ValueError as error:
        assert "zero environment forcing" in str(error)
    else:
        raise AssertionError("cross-check must reject unsupported forcing")
