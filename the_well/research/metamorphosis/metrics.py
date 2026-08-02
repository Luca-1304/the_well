"""Diagnostics for boundedness, vorticity, and vorticity-equation balance."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor


@dataclass(frozen=True)
class ContinuationMetrics:
    max_velocity_gradient: float
    max_vorticity: float
    kinetic_energy: float
    vortex_stretching_rate: float
    viscous_redistribution_rate: float

    @property
    def concentration_rate(self) -> float:
        """Compatibility name for the stretching diagnostic."""
        return self.vortex_stretching_rate

    @property
    def redistribution_rate(self) -> float:
        """Compatibility name for the viscous-diffusion diagnostic."""
        return self.viscous_redistribution_rate

    @property
    def regulation_ratio(self) -> float:
        """Dimensionless norm ratio; diagnostic only, not a regularity theorem."""
        if self.viscous_redistribution_rate <= 0:
            return 0.0 if self.vortex_stretching_rate <= 0 else float("inf")
        return self.vortex_stretching_rate / self.viscous_redistribution_rate

    @property
    def redistribution_dominates(self) -> bool:
        return self.regulation_ratio <= 1.0

    @property
    def controlled(self) -> bool:
        """Backward-compatible alias for redistribution_dominates."""
        return self.redistribution_dominates


def velocity_jacobian(velocity: Tensor, spacing: tuple[float, ...]) -> Tensor:
    """Finite-difference Jacobian with shape (..., component, derivative_axis)."""
    spatial_dims = velocity.ndim - 1
    if spatial_dims not in (2, 3):
        raise ValueError("velocity must describe a 2D or 3D spatial grid")
    if velocity.shape[-1] != spatial_dims:
        raise ValueError("velocity components must match spatial dimensions")
    if len(spacing) != spatial_dims:
        raise ValueError("spacing must match the number of spatial dimensions")
    if any(step <= 0 for step in spacing):
        raise ValueError("spacing values must be positive")

    rows = []
    axes = tuple(range(spatial_dims))
    for component in range(velocity.shape[-1]):
        derivatives = torch.gradient(
            velocity[..., component],
            spacing=spacing,
            dim=axes,
        )
        rows.append(torch.stack(derivatives, dim=-1))
    return torch.stack(rows, dim=-2)


def scalar_laplacian_grid(field: Tensor, spacing: tuple[float, ...]) -> Tensor:
    """Finite-difference Laplacian of a scalar field on a regular grid."""
    if field.ndim != len(spacing):
        raise ValueError("scalar field dimensions must match spacing")
    if any(step <= 0 for step in spacing):
        raise ValueError("spacing values must be positive")

    terms = []
    for axis, step in enumerate(spacing):
        first = torch.gradient(field, spacing=(step,), dim=(axis,))[0]
        second = torch.gradient(first, spacing=(step,), dim=(axis,))[0]
        terms.append(second)
    return torch.stack(terms, dim=0).sum(dim=0)


def vector_laplacian_grid(field: Tensor, spacing: tuple[float, ...]) -> Tensor:
    """Finite-difference Laplacian applied componentwise to a vector field."""
    if field.ndim - 1 != len(spacing):
        raise ValueError("vector field dimensions must match spacing")
    return torch.stack(
        [scalar_laplacian_grid(field[..., i], spacing) for i in range(field.shape[-1])],
        dim=-1,
    )


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


def scalar_linf(field: Tensor) -> Tensor:
    return field.abs().amax()


def vector_linf(field: Tensor) -> Tensor:
    if field.shape[-1] not in (2, 3):
        raise ValueError("expected a 2D or 3D vector field")
    return torch.linalg.vector_norm(field, dim=-1).amax()


def velocity_gradient_linf(jacobian: Tensor) -> Tensor:
    """Essential-supremum proxy using the pointwise Frobenius norm of ∇u."""
    if jacobian.shape[-2:] not in ((2, 2), (3, 3)):
        raise ValueError("jacobian must end in a 2x2 or 3x3 matrix")
    return torch.linalg.matrix_norm(jacobian, ord="fro", dim=(-2, -1)).amax()


def vorticity_linf(omega: Tensor) -> Tensor:
    if omega.ndim > 0 and omega.shape[-1] == 3:
        return vector_linf(omega)
    return scalar_linf(omega)


def kinetic_energy(
    velocity: Tensor,
    cell_volume: float = 1.0,
    density: float = 1.0,
) -> Tensor:
    if cell_volume <= 0 or density <= 0:
        raise ValueError("cell_volume and density must be positive")
    speed_squared = (velocity * velocity).sum(dim=-1)
    return 0.5 * density * speed_squared.sum() * cell_volume


def vorticity_balance_terms(
    velocity: Tensor,
    spacing: tuple[float, ...],
    viscosity: float,
) -> tuple[Tensor, Tensor]:
    """Return vortex-stretching and viscous-diffusion terms.

    In 3D:
        stretching = (ω·∇)u
        diffusion = ν Δω

    In 2D the vortex-stretching term is identically zero, which is why a 2D
    run validates infrastructure but cannot directly probe the 3D mechanism.
    """
    if viscosity < 0:
        raise ValueError("viscosity cannot be negative")

    jac = velocity_jacobian(velocity, spacing)
    omega = vorticity(velocity, spacing)

    if velocity.ndim - 1 == 2:
        stretching = torch.zeros_like(omega)
        diffusion = viscosity * scalar_laplacian_grid(omega, spacing)
        return stretching, diffusion

    stretching = torch.einsum("...ij,...j->...i", jac, omega)
    diffusion = viscosity * vector_laplacian_grid(omega, spacing)
    return stretching, diffusion


def compute_metrics(
    velocity: Tensor,
    spacing: tuple[float, ...],
    *,
    viscosity: float,
    density: float = 1.0,
) -> ContinuationMetrics:
    jac = velocity_jacobian(velocity, spacing)
    omega = vorticity(velocity, spacing)
    stretching, diffusion = vorticity_balance_terms(velocity, spacing, viscosity)
    cell_volume = float(torch.tensor(spacing).prod())
    stretch_norm = (
        vector_linf(stretching)
        if stretching.ndim == velocity.ndim
        else scalar_linf(stretching)
    )
    diffusion_norm = (
        vector_linf(diffusion)
        if diffusion.ndim == velocity.ndim
        else scalar_linf(diffusion)
    )

    return ContinuationMetrics(
        max_velocity_gradient=float(velocity_gradient_linf(jac).detach().cpu()),
        max_vorticity=float(vorticity_linf(omega).detach().cpu()),
        kinetic_energy=float(
            kinetic_energy(velocity, cell_volume, density).detach().cpu()
        ),
        vortex_stretching_rate=float(stretch_norm.detach().cpu()),
        viscous_redistribution_rate=float(diffusion_norm.detach().cpu()),
    )
