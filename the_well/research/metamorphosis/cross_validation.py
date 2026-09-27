"""Cross-validate the 3D spectral solver against a distinct FD/RK2 path."""

from __future__ import annotations

from dataclasses import dataclass, replace

import torch

from .solver3d import PeriodicSpectralNavierStokes3D, SpectralSimulationConfig
from .solver_fd3d import PeriodicFiniteDifferenceNavierStokes3D


@dataclass(frozen=True)
class CrossSolverComparison:
    velocity_relative_l2: float
    kinetic_energy_relative_error: float
    max_vorticity_relative_error: float
    spectral_steps: int
    finite_difference_steps: int


def _relative_scalar_error(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-12)


def compare_uncontrolled_solvers(
    config: SpectralSimulationConfig,
) -> CrossSolverComparison:
    """Run the same uncontrolled periodic initial state through both solvers."""
    clean = replace(
        config,
        controller_enabled=False,
        observation_mismatch=0.0,
        base_uncertainty=0.0,
        control_risk=0.0,
        external_risk=0.0,
    )
    if clean.boundary.environmental_strength != 0.0:
        raise ValueError("cross-solver comparison requires zero environment forcing")

    spectral_solver = PeriodicSpectralNavierStokes3D(clean)
    spectral_state, spectral_records = spectral_solver.run()
    spectral_velocity = spectral_solver.physical_velocity(spectral_state)

    finite_difference_solver = PeriodicFiniteDifferenceNavierStokes3D(clean)
    fd_velocity, fd_records = finite_difference_solver.run()

    difference = torch.linalg.vector_norm(
        (spectral_velocity - fd_velocity).reshape(-1)
    )
    reference = torch.linalg.vector_norm(spectral_velocity.reshape(-1))
    velocity_relative_l2 = float(
        (difference / (reference + torch.finfo(spectral_velocity.dtype).eps))
        .detach()
        .cpu()
    )

    spectral_energy = spectral_records[-1].kinetic_energy
    fd_energy = fd_records[-1].kinetic_energy

    spectral_omega = spectral_solver.spectral_vorticity(
        spectral_state.velocity_hat
    )
    spectral_max_omega = float(
        torch.linalg.vector_norm(spectral_omega, dim=-1)
        .amax()
        .detach()
        .cpu()
    )
    fd_max_omega = fd_records[-1].max_vorticity

    return CrossSolverComparison(
        velocity_relative_l2=velocity_relative_l2,
        kinetic_energy_relative_error=_relative_scalar_error(
            spectral_energy,
            fd_energy,
        ),
        max_vorticity_relative_error=_relative_scalar_error(
            spectral_max_omega,
            fd_max_omega,
        ),
        spectral_steps=len(spectral_records),
        finite_difference_steps=len(fd_records),
    )
