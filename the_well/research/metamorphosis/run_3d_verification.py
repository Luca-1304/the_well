"""Run the complete first-stage 3D Metamorphosis verification battery."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .convergence import resolution_sweep, timestep_sweep
from .robustness import amplitude_robustness_sweep
from .run_3d_simulation import run_twin_experiment
from .solver3d import SpectralSimulationConfig


def run_verification_battery(
    config: SpectralSimulationConfig,
    *,
    grid_sizes: tuple[int, ...] = (8, 12, 16),
    time_steps: tuple[float, ...] | None = None,
    amplitude_perturbations: tuple[float, ...] = (-0.05, 0.05, 0.10),
) -> dict[str, object]:
    if time_steps is None:
        time_steps = (
            config.time_step,
            config.time_step / 2.0,
            config.time_step / 4.0,
        )

    twin = run_twin_experiment(config, cross_validate=True)
    resolution_points, resolution_differences = resolution_sweep(
        config,
        grid_sizes,
    )
    timestep_points, timestep_differences = timestep_sweep(
        config,
        time_steps,
    )
    robustness_points, flip_margin = amplitude_robustness_sweep(
        config,
        amplitude_perturbations,
    )

    return {
        "twin_experiment": twin,
        "resolution_sweep": {
            "points": [asdict(point) for point in resolution_points],
            "consecutive_differences": [
                asdict(difference) for difference in resolution_differences
            ],
        },
        "timestep_sweep": {
            "points": [asdict(point) for point in timestep_points],
            "consecutive_differences": [
                asdict(difference) for difference in timestep_differences
            ],
        },
        "amplitude_robustness": {
            "points": [asdict(point) for point in robustness_points],
            "minimum_tested_flip_margin": flip_margin,
        },
        "claims_boundary": (
            "This battery supplies finite-resolution verification evidence. "
            "It cannot prove global regularity or a finite-time singularity."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-size", type=int, default=16)
    parser.add_argument("--viscosity", type=float, default=1.0e-2)
    parser.add_argument("--time-step", type=float, default=2.0e-3)
    parser.add_argument("--final-time", type=float, default=2.0e-2)
    args = parser.parse_args()

    config = SpectralSimulationConfig(
        grid_size=args.grid_size,
        viscosity=args.viscosity,
        time_step=args.time_step,
        final_time=args.final_time,
    )
    print(json.dumps(run_verification_battery(config), indent=2))


if __name__ == "__main__":
    main()
