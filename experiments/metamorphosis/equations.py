"""Equation contracts for the Navier–Stokes Metamorphosis research track.

This module deliberately contains residual definitions and typed parameters,
not a claim of a Navier–Stokes proof. It is designed for conventional solvers,
PINNs, and dataset diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import torch
from torch import Tensor


class VectorField(Protocol):
    def __call__(self, x: Tensor, t: Tensor) -> Tensor: ...


@dataclass(frozen=True)
class FluidParameters:
    density: float = 1.0
    kinematic_viscosity: float = 1.0e-3
    heat_capacity: float = 1.0
    thermal_conductivity: float = 1.0e-3
    scalar_diffusivity: float = 1.0e-4
    thermal_expansion: float = 0.0
    reference_temperature: float = 0.0

    def validate(self) -> None:
        if self.density <= 0:
            raise ValueError("density must be positive")
        if self.kinematic_viscosity <= 0:
            raise ValueError("kinematic_viscosity must be positive")
        if self.heat_capacity <= 0:
            raise ValueError("heat_capacity must be positive")
        if self.thermal_conductivity <= 0:
            raise ValueError("thermal_conductivity must be positive")
        if self.scalar_diffusivity < 0:
            raise ValueError("scalar_diffusivity cannot be negative")


def spatial_gradient_scalar(value: Tensor, x: Tensor) -> Tensor:
    """Return ∇value for a scalar field sampled at x."""
    return torch.autograd.grad(
        value,
        x,
        grad_outputs=torch.ones_like(value),
        create_graph=True,
        retain_graph=True,
    )[0]


def divergence(vector: Tensor, x: Tensor) -> Tensor:
    """Return ∇·vector for batched 2D or 3D vector samples."""
    if vector.shape[-1] != x.shape[-1]:
        raise ValueError("vector and coordinate dimensions must match")
    terms = []
    for component in range(vector.shape[-1]):
        grad = torch.autograd.grad(
            vector[..., component],
            x,
            grad_outputs=torch.ones_like(vector[..., component]),
            create_graph=True,
            retain_graph=True,
        )[0]
        terms.append(grad[..., component])
    return torch.stack(terms, dim=-1).sum(dim=-1)


def laplacian_scalar(value: Tensor, x: Tensor) -> Tensor:
    """Return Δvalue for a scalar field."""
    grad = spatial_gradient_scalar(value, x)
    terms = []
    for component in range(x.shape[-1]):
        second = torch.autograd.grad(
            grad[..., component],
            x,
            grad_outputs=torch.ones_like(grad[..., component]),
            create_graph=True,
            retain_graph=True,
        )[0][..., component]
        terms.append(second)
    return torch.stack(terms, dim=-1).sum(dim=-1)


def laplacian_vector(vector: Tensor, x: Tensor) -> Tensor:
    """Return the componentwise vector Laplacian."""
    return torch.stack(
        [laplacian_scalar(vector[..., i], x) for i in range(vector.shape[-1])],
        dim=-1,
    )


def time_derivative(value: Tensor, t: Tensor) -> Tensor:
    """Return ∂value/∂t for independently sampled batched points."""
    return torch.autograd.grad(
        value,
        t,
        grad_outputs=torch.ones_like(value),
        create_graph=True,
        retain_graph=True,
    )[0]


def navier_stokes_residual(
    velocity: Tensor,
    pressure: Tensor,
    x: Tensor,
    t: Tensor,
    parameters: FluidParameters,
    control_force: Tensor | None = None,
) -> tuple[Tensor, Tensor]:
    """Return momentum and incompressibility residuals.

    Residual convention:
        u_t + (u·∇)u + ∇p/ρ - νΔu - f_control = 0
        ∇·u = 0
    """
    parameters.validate()
    dimension = velocity.shape[-1]
    if dimension not in (2, 3) or x.shape[-1] != dimension:
        raise ValueError("velocity and coordinates must describe 2D or 3D space")
    if control_force is None:
        control_force = torch.zeros_like(velocity)
    if control_force.shape != velocity.shape:
        raise ValueError("control_force must match velocity shape")

    du_dt = torch.stack(
        [time_derivative(velocity[..., i], t).squeeze(-1) for i in range(dimension)],
        dim=-1,
    )

    convection = torch.stack(
        [
            (velocity * spatial_gradient_scalar(velocity[..., i], x)).sum(dim=-1)
            for i in range(dimension)
        ],
        dim=-1,
    )

    pressure_gradient = spatial_gradient_scalar(pressure, x)
    diffusion = parameters.kinematic_viscosity * laplacian_vector(velocity, x)

    momentum = (
        du_dt
        + convection
        + pressure_gradient / parameters.density
        - diffusion
        - control_force
    )
    return momentum, divergence(velocity, x)


def temperature_residual(
    temperature: Tensor,
    velocity: Tensor,
    x: Tensor,
    t: Tensor,
    parameters: FluidParameters,
    heat_source: Tensor | None = None,
) -> Tensor:
    """Return residual of ρ c_p(T_t + u·∇T) = kΔT + Q."""
    parameters.validate()
    if heat_source is None:
        heat_source = torch.zeros_like(temperature)
    if heat_source.shape != temperature.shape:
        raise ValueError("heat_source must match temperature shape")

    dT_dt = time_derivative(temperature, t).squeeze(-1)
    advection = (velocity * spatial_gradient_scalar(temperature, x)).sum(dim=-1)
    diffusion = parameters.thermal_conductivity * laplacian_scalar(temperature, x)

    return (
        parameters.density * parameters.heat_capacity * (dT_dt + advection)
        - diffusion
        - heat_source
    )


def passive_scalar_residual(
    scalar: Tensor,
    velocity: Tensor,
    x: Tensor,
    t: Tensor,
    parameters: FluidParameters,
    source: Tensor | None = None,
) -> Tensor:
    """Return residual of c_t + u·∇c = κ_c Δc + source.

    The passive scalar is the first computational representation of the marked
    substance X. It tracks material concentration without changing momentum.
    """
    parameters.validate()
    if source is None:
        source = torch.zeros_like(scalar)
    if source.shape != scalar.shape:
        raise ValueError("source must match scalar shape")

    dc_dt = time_derivative(scalar, t).squeeze(-1)
    advection = (velocity * spatial_gradient_scalar(scalar, x)).sum(dim=-1)
    diffusion = parameters.scalar_diffusivity * laplacian_scalar(scalar, x)
    return dc_dt + advection - diffusion - source
