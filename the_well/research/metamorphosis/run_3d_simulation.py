"""Run twin uncontrolled/controlled 3D Taylor–Green experiments."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace

from .controller import ControllerConfig
from .safety import BoundaryMode, BoundaryState
from .solver3d import PeriodicSpectralNavierStokes3D, SpectralSimulationConfig


def build_boundary(
    mode: BoundaryMode,
    *,
    capacity: float,
    permeability: float,
    coupling: float,
    environmental_strength: float,
) -> BoundaryState:
    if mode is BoundaryMode.CLOSED_STRONG:
        permeability = 0.0
    return BoundaryState(
        mode=mode,
        load=0.0,
        capacity=capacity,
        permeability=permeability,
        coupling=coupling,
        environmental_strength=environmental_strength,
    )


def summarise(records: list[object]) -> dict[str, object]:
    if not records:
        return {"steps": 0}

    last = records[-1]
    peak_gradient = max(record.max_velocity_gradient for record in records)
    peak_vorticity = max(record.max_vorticity for record in records)
    peak_stretching = max(record.vortex_stretching_rate for record in records)
    minimum_mass_fidelity = min(record.scalar_mass_fidelity for record in records)
    maximum_control_effort = max(record.control_effort for record in records)
    return {
        "steps": len(records),
        "final": asdict(last),
        "peak_velocity_gradient": peak_gradient,
        "peak_vorticity": peak_vorticity,
        "peak_vortex_stretching_rate": peak_stretching,
        "minimum_scalar_mass_fidelity": minimum_mass_fidelity,
        "maximum_control_effort": maximum_control_effort,
        "all_predictions_trusted": all(
            record.trusted_prediction for record in records
        ),
    }


def run_twin_experiment(
    config: SpectralSimulationConfig,
) -> dict[str, object]:
    uncontrolled_config = replace(config, controller_enabled=False)
    controlled_config = replace(config, controller_enabled=True)

    _, uncontrolled_records = PeriodicSpectralNavierStokes3D(
        uncontrolled_config
    ).run()
    _, controlled_records = PeriodicSpectralNavierStokes3D(
        controlled_config
    ).run()

    return {
        "uncontrolled": summarise(uncontrolled_records),
        "controlled": summarise(controlled_records),
        "claims_boundary": (
            "Finite-resolution engineering evidence only; not a proof of "
            "Navier-Stokes regularity or singularity."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-size", type=int, default=16)
    parser.add_argument("--viscosity", type=float, default=1.0e-2)
    parser.add_argument("--scalar-diffusivity", type=float, default=1.0e-3)
    parser.add_argument("--time-step", type=float, default=2.0e-3)
    parser.add_argument("--final-time", type=float, default=2.0e-2)
    parser.add_argument(
        "--boundary-mode",
        choices=[mode.value for mode in BoundaryMode],
        default=BoundaryMode.CLOSED_STRONG.value,
    )
    parser.add_argument("--boundary-capacity", type=float, default=10.0)
    parser.add_argument("--permeability", type=float, default=0.5)
    parser.add_argument("--coupling", type=float, default=1.0)
    parser.add_argument("--environmental-strength", type=float, default=0.0)
    parser.add_argument("--environment-sign", type=float, choices=(-1.0, 1.0), default=1.0)
    parser.add_argument("--safe-vorticity", type=float, default=1.0)
    parser.add_argument("--controller-gain", type=float, default=0.1)
    parser.add_argument("--max-control-force", type=float, default=1.0)
    parser.add_argument("--observation-mismatch", type=float, default=0.0)
    parser.add_argument("--base-uncertainty", type=float, default=0.0)
    args = parser.parse_args()

    boundary = build_boundary(
        BoundaryMode(args.boundary_mode),
        capacity=args.boundary_capacity,
        permeability=args.permeability,
        coupling=args.coupling,
        environmental_strength=args.environmental_strength,
    )
    controller = ControllerConfig(
        safe_vorticity=args.safe_vorticity,
        proportional_gain=args.controller_gain,
        max_control_force=args.max_control_force,
    )
    config = SpectralSimulationConfig(
        grid_size=args.grid_size,
        viscosity=args.viscosity,
        scalar_diffusivity=args.scalar_diffusivity,
        time_step=args.time_step,
        final_time=args.final_time,
        boundary=boundary,
        environment_sign=args.environment_sign,
        controller=controller,
        observation_mismatch=args.observation_mismatch,
        base_uncertainty=args.base_uncertainty,
    )
    print(json.dumps(run_twin_experiment(config), indent=2))


if __name__ == "__main__":
    main()
