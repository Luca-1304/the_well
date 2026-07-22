"""Diagnostics for boundedness, vorticity, continuation, and control balance."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor


@dataclass(frozen=True)
class ContinuationMetrics:
    max_velocity_gradient: float
    max_vorticity: float
    kinetic_energy: float
    concentration_rate: float
    redistribution_rate: float

    @property
    def regulation_ratio(self) -> float:
        if self.redistribution_rate <= 0:
            return float("inf")
        return self.concentration_rate / self.redistribution_rate

    @property
    def controlled(self) -> bool:
        return self.regulation_ratio <= 1.0


def velocity_jacobian(velocity: Tensor, spacing: tuple[float, ...]) -> Tensor:
    """Finite-difference Jacobian with shape (..., component, derivative_axis)."""
    spatial_dims = velocity.ndim - 1
    if spatial_dims not in (2, 3):
        raise ValueError("velocity must describe a 2D or 3D spatial grid")
    if len(spacing) != spatial_dims:
        raise ValueError("spacing must match the number of spatial dimensions")

    rows = []
    for component in range(velocity.shape[-1]):
        component_field = velocity[..., component]
        derivatives = torch.gradient(component_field, spacing=spacing, dim=tuple(range(spatial_dims)))
        rows.append(torch.stack(derivatives, dim=-1))
    return torch.stack(rows, dim=-2)


def vorticity(velocity: Tensor, spacing: tuple[float, ...]) -> Tensor:
    """Return scalar 2D vorticity or vector 3D curl."""
    jac = velocity_jacobian(velocity, spacing)
    spatial_dims = velocity.ndim - 1
    if spatial_dims == 2:
        return jac[..., 1, 0] - jac[..., 0, 1]

    return torch.stack(
        (
            jac[..., 2, 1] - jac[..., 1, 2],
            jac[..., 0, 2] - jac[..., 2, 0],
            jac[..., 1, 0] - jac[..., 0, 1],
        ),
        dim=-1,
    )


def infinity_norm(field: Tensor) -> Tensor:
    """Maximum absolute scalar value or vector magnitude."""
    if field.ndim > 0 and field.shape[-1] in (2, 3):
        return torch.linalg.vector_norm(field, dim=-1).amax()
    return field.abs().amax()


def kinetic_energy(velocity: Tensor, cell_volume: float = 1.0, density: float = 1.0) -> Tensor:
    if cell_volume <= 0 or density <= 0:
        raise ValueError("cell_volume and density must be positive")
    speed_squared = (velocity * velocity).sum(dim=-1)
    return 0.5 * density * speed_squared.sum() * cell_volume


def compute_metrics(
    velocity: Tensor,
    spacing: tuple[float, ...],
    *,
    concentration_rate: float,
    redistribution_rate: float,
    density: float = 1.0,
) -> ContinuationMetrics:
    jac = velocity_jacobian(velocity, spacing)
    omega = vorticity(velocity, spacing)
    cell_volume = float(torch.tensor(spacing).prod())
    return ContinuationMetrics(
        max_velocity_gradient=float(infinity_norm(jac).detach().cpu()),
        max_vorticity=float(infinity_norm(omega).detach().cpu()),
        kinetic_energy=float(kinetic_energy(velocity, cell_volume, density).detach().cpu()),
        concentration_rate=float(concentration_rate),
        redistribution_rate=float(redistribution_rate),
    )
