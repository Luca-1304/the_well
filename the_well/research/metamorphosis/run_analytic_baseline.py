"""Run a deterministic 2D Taylor–Green diagnostic baseline.

This is an infrastructure check for the differential operators and metrics.
Because 2D incompressible flow has no vortex-stretching term, this run cannot
test the central 3D regularity mechanism.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict

import torch

from .metrics import compute_metrics


def taylor_green_velocity(
    x: torch.Tensor,
    y: torch.Tensor,
    *,
    time: float,
    viscosity: float,
) -> torch.Tensor:
    decay = math.exp(-2.0 * viscosity * time)
    u = torch.sin(x) * torch.cos(y) * decay
    v = -torch.cos(x) * torch.sin(y) * decay
    return torch.stack((u, v), dim=-1)


def run_baseline(
    *,
    grid_size: int = 64,
    viscosity: float = 1.0e-3,
    density: float = 1.0,
    times: tuple[float, ...] = (0.0, 0.25, 0.5, 1.0),
) -> list[dict[str, float]]:
    if grid_size < 8:
        raise ValueError("grid_size must be at least 8")
    if viscosity <= 0:
        raise ValueError("viscosity must be positive")
    if density <= 0:
        raise ValueError("density must be positive")
    if any(time < 0 for time in times):
        raise ValueError("times cannot be negative")

    domain_length = 2.0 * math.pi
    spacing = domain_length / grid_size
    coordinates = torch.arange(grid_size, dtype=torch.float64) * spacing
    x, y = torch.meshgrid(coordinates, coordinates, indexing="ij")

    results: list[dict[str, float]] = []
    for time in times:
        velocity = taylor_green_velocity(
            x,
            y,
            time=time,
            viscosity=viscosity,
        )
        metrics = compute_metrics(
            velocity,
            (spacing, spacing),
            viscosity=viscosity,
            density=density,
        )
        record = {"time": float(time), **asdict(metrics)}
        record["regulation_ratio"] = metrics.regulation_ratio
        results.append(record)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-size", type=int, default=64)
    parser.add_argument("--viscosity", type=float, default=1.0e-3)
    parser.add_argument("--density", type=float, default=1.0)
    args = parser.parse_args()

    results = run_baseline(
        grid_size=args.grid_size,
        viscosity=args.viscosity,
        density=args.density,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
