from __future__ import annotations

from the_well.research.metamorphosis.controller import ControllerConfig
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


def open_environment(sign: float) -> SpectralSimulationConfig:
    return SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=5.0e-4,
        boundary=BoundaryState(
            mode=BoundaryMode.OPEN,
            load=0.0,
            capacity=10.0,
            permeability=1.0,
            coupling=1.0,
            environmental_strength=0.1,
        ),
        environment_sign=sign,
        environment_component_weights=(1.0, 1.0, 0.0),
        verification_scales=permissive_scales(),
    )


def controlled_config(sign: float) -> SpectralSimulationConfig:
    return SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=5.0e-4,
        controller_enabled=True,
        controller=ControllerConfig(
            safe_vorticity=0.1,
            proportional_gain=0.2,
            max_control_force=0.5,
        ),
        controller_sign=sign,
        verification_scales=permissive_scales(),
    )


def test_environment_sign_changes_actual_projected_power_direction() -> None:
    _, aggravating = PeriodicSpectralNavierStokes3D(
        open_environment(1.0)
    ).run()
    _, opposing = PeriodicSpectralNavierStokes3D(
        open_environment(-1.0)
    ).run()

    assert aggravating[0].environmental_power > 0.0
    assert opposing[0].environmental_power < 0.0
    assert aggravating[0].energy_power_dominance_ratio > 0.0
    assert opposing[0].energy_power_dominance_ratio == 0.0


def test_controller_sign_reversal_is_visible_in_power_accounting() -> None:
    _, damping = PeriodicSpectralNavierStokes3D(controlled_config(1.0)).run()
    _, reversed_control = PeriodicSpectralNavierStokes3D(
        controlled_config(-1.0)
    ).run()

    assert damping[0].control_power < 0.0
    assert reversed_control[0].control_power > 0.0


def test_hard_watchdog_can_override_soft_risk_decision() -> None:
    config = SpectralSimulationConfig(
        grid_size=8,
        viscosity=5.0e-2,
        scalar_diffusivity=1.0e-2,
        time_step=5.0e-4,
        final_time=5.0e-4,
        watchdog_energy_residual_limit=1.0e-15,
        verification_scales=permissive_scales(),
    )
    _, records = PeriodicSpectralNavierStokes3D(config).run()

    assert records[0].watchdog_triggered
    assert records[0].safety_mode == "isolate"
    assert records[0].authority_scale == 0.0
    assert not records[0].trusted_prediction
