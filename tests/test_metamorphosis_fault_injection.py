from __future__ import annotations

from the_well.research.metamorphosis.controller import ControllerConfig
from the_well.research.metamorphosis.safety import VerificationScales
from the_well.research.metamorphosis.solver3d import (
    PeriodicSpectralNavierStokes3D,
    SpectralSimulationConfig,
)


def scales() -> VerificationScales:
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


def test_controller_delay_withholds_action_until_history_exists() -> None:
    config = SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=1.0e-3,
        controller_enabled=True,
        controller_delay_steps=1,
        controller=ControllerConfig(
            safe_vorticity=0.1,
            proportional_gain=0.1,
            max_control_force=10.0,
        ),
        verification_scales=scales(),
    )

    _, records = PeriodicSpectralNavierStokes3D(config).run()

    assert len(records) == 2
    assert records[0].control_effort == 0.0
    assert records[1].control_effort > 0.0


def test_sensor_scale_changes_unsaturated_controller_effort() -> None:
    base = dict(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=5.0e-4,
        controller_enabled=True,
        controller=ControllerConfig(
            safe_vorticity=0.1,
            proportional_gain=0.01,
            max_control_force=100.0,
        ),
        verification_scales=scales(),
    )
    _, nominal = PeriodicSpectralNavierStokes3D(
        SpectralSimulationConfig(
            **base,
            sensor_vorticity_scale=1.0,
        )
    ).run()
    _, drifted = PeriodicSpectralNavierStokes3D(
        SpectralSimulationConfig(
            **base,
            sensor_vorticity_scale=2.0,
        )
    ).run()

    assert drifted[0].control_effort > nominal[0].control_effort
