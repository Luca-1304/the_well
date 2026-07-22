"""Equation contracts for the Navier–Stokes Metamorphosis research track.

This module deliberately contains residual definitions and typed parameters,
not a claim of a Navier–Stokes proof.  It is designed for use by conventional
solvers, PINNs, and dataset diagnostics.
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


def spatial_gradient_scalar(value: Tensor, x: Tensor) -> Tensor:
    """Return ∇value for a scalar field sampled at x."""
    grad = torch.autograd.grad(
        value,
        x,
        grad_outputs=torch.ones_like(value),
        create_graph=True,
        retain_graph=True,
    )[0]
    return grad


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
    second_terms = []
    for component in range(x.shape[-1]):
        second = torch.autograd.grad(
            grad[..., component],
            x,
            grad_outputs=torch.ones_like(grad[..., component]),
            create_graph=True,
            retain_graph=True,
        )[0][..., component]
        second_terms.append(second)
    return torch.stack(second_terms, dim=-1).sum(dim=-1)


def laplacian_vector(vector: Tensor, x: Tensor) -> Tensor:
    return torch.stack(
        [laplacian_scalar(vector[..., i], x) for i in range(vector.shape[-1])],
        dim=-1,
    )


def time_derivative(value: Tensor, t: Tensor) -> Tensor:
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

    Assumes pressure is already divided by any desired nondimensional scale.
    """
    parameters.validate()
    dimension = velocity.shape[-1]
    if control_force is None:
        control_force = torch.zeros_like(velocity)
    if control_force.shape != velocity.shape:
        raise ValueError("control_force must match velocity shape")

    du_dt = torch.stack(
        [time_derivative(velocity[..., i], t).squeeze(-1) for i in range(dimension)],
        dim=-1,
    )

    convection_components = []
    for i in range(dimension):
        grad_ui = spatial_gradient_scalar(velocity[..., i], x)
        convection_components.append((velocity * grad_ui).sum(dim=-1))
    convection = torch.stack(convection_components, dim=-1)

    pressure_gradient = spatial_gradient_scalar(pressure, x)
    diffusion = parameters.kinematic_viscosity * laplacian_vector(velocity, x)

    momentum = (
        du_dt
        + convection
        + pressure_gradient / parameters.density
        - diffusion
        - control_force
    )
    continuity = divergence(velocity, x)
    return momentum, continuity


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

    dT_dt = time_derivative(temperature, t).squeeze(-1)
    grad_T = spatial_gradient_scalar(temperature, x)
    advection = (velocity * grad_T).sum(dim=-1)
    diffusion = parameters.thermal_conductivity * laplacian_scalar(temperature, x)

    return (
        parameters.density
        * parameters.heat_capacity
        * (dT_dt + advection)
        - diffusion
        - heat_source
    )
