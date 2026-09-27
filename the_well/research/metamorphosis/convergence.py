"""Grid and timestep convergence harness for the 3D Metamorphosis solver."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Sequence

from .solver3d import PeriodicSpectralNavierStokes3D, SpectralSimulationConfig


@dataclass(frozen=True)
class ConvergencePoint:
    grid_size: int
    time_step: float
    final_time: float
    final_velocity_gradient: float
    final_vorticity: float
    final_kinetic_energy: float
    peak_velocity_gradient: float
    peak_vorticity: float
    max_divergence_residual: float
    max_pde_residual: float
    max_energy_residual: float
    max_spectral_tail_fraction: float
    all_predictions_trusted: bool


@dataclass(frozen=True)
class ConsecutiveDifference:
    coarse_label: str
    fine_label: str
    velocity_gradient_relative_difference: float
    vorticity_relative_difference: float
    kinetic_energy_relative_difference: float


def _relative_difference(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-12)


def _run_point(config: SpectralSimulationConfig) -> ConvergencePoint:
    _, records = PeriodicSpectralNavierStokes3D(config).run()
    if not records:
        raise RuntimeError("convergence run produced no records")
    final = records[-1]
    return ConvergencePoint(
        grid_size=config.grid_size,
        time_step=config.time_step,
        final_time=final.time,
        final_velocity_gradient=final.max_velocity_gradient,
        final_vorticity=final.max_vorticity,
        final_kinetic_energy=final.kinetic_energy,
        peak_velocity_gradient=max(record.max_velocity_gradient for record in records),
        peak_vorticity=max(record.max_vorticity for record in records),
        max_divergence_residual=max(record.divergence_residual for record in records),
        max_pde_residual=max(record.pde_residual for record in records),
        max_energy_residual=max(record.energy_residual for record in records),
        max_spectral_tail_fraction=max(
            record.spectral_tail_fraction for record in records
        ),
        all_predictions_trusted=all(record.trusted_prediction for record in records),
    )


def resolution_sweep(
    config: SpectralSimulationConfig,
    grid_sizes: Sequence[int],
) -> tuple[list[ConvergencePoint], list[ConsecutiveDifference]]:
    if len(grid_sizes) < 2:
        raise ValueError("resolution sweep requires at least two grid sizes")

    points = [
        _run_point(replace(config, grid_size=grid_size)) for grid_size in grid_sizes
    ]
    differences = []
    for coarse, fine in zip(points, points[1:]):
        differences.append(
            ConsecutiveDifference(
                coarse_label=f"N={coarse.grid_size}",
                fine_label=f"N={fine.grid_size}",
                velocity_gradient_relative_difference=_relative_difference(
                    coarse.final_velocity_gradient,
                    fine.final_velocity_gradient,
                ),
                vorticity_relative_difference=_relative_difference(
                    coarse.final_vorticity,
                    fine.final_vorticity,
                ),
                kinetic_energy_relative_difference=_relative_difference(
                    coarse.final_kinetic_energy,
                    fine.final_kinetic_energy,
                ),
            )
        )
    return points, differences


def timestep_sweep(
    config: SpectralSimulationConfig,
    time_steps: Sequence[float],
) -> tuple[list[ConvergencePoint], list[ConsecutiveDifference]]:
    if len(time_steps) < 2:
        raise ValueError("timestep sweep requires at least two time steps")
    if any(step <= 0 or not math.isfinite(step) for step in time_steps):
        raise ValueError("time steps must be finite and positive")

    points = [
        _run_point(replace(config, time_step=time_step)) for time_step in time_steps
    ]
    differences = []
    for coarse, fine in zip(points, points[1:]):
        differences.append(
            ConsecutiveDifference(
                coarse_label=f"dt={coarse.time_step}",
                fine_label=f"dt={fine.time_step}",
                velocity_gradient_relative_difference=_relative_difference(
                    coarse.final_velocity_gradient,
                    fine.final_velocity_gradient,
                ),
                vorticity_relative_difference=_relative_difference(
                    coarse.final_vorticity,
                    fine.final_vorticity,
                ),
                kinetic_energy_relative_difference=_relative_difference(
                    coarse.final_kinetic_energy,
                    fine.final_kinetic_energy,
                ),
            )
        )
    return points, differences
