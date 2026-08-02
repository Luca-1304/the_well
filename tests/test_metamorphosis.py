from __future__ import annotations

import math

import pytest
import torch

from the_well.research.metamorphosis.equations import (
    FluidParameters,
    navier_stokes_residual,
    passive_scalar_residual,
    temperature_residual,
)
from the_well.research.metamorphosis.metrics import (
    compute_metrics,
    vorticity,
    vorticity_balance_terms,
)
from the_well.research.metamorphosis.preservation import (
    compute_marked_scalar_metrics,
    mass_fidelity,
    soft_overlap,
)


def test_taylor_green_satisfies_navier_stokes_residual() -> None:
    torch.set_default_dtype(torch.float64)
    sample_count = 64
    viscosity = 1.0e-2

    x = (2.0 * math.pi * torch.rand(sample_count, 2)).requires_grad_()
    t = torch.rand(sample_count, 1, requires_grad=True)
    decay = torch.exp(-2.0 * viscosity * t[:, 0])

    velocity = torch.stack(
        (
            torch.sin(x[:, 0]) * torch.cos(x[:, 1]) * decay,
            -torch.cos(x[:, 0]) * torch.sin(x[:, 1]) * decay,
        ),
        dim=-1,
    )
    pressure = (
        0.25
        * (torch.cos(2.0 * x[:, 0]) + torch.cos(2.0 * x[:, 1]))
        * torch.exp(-4.0 * viscosity * t[:, 0])
    )

    momentum, continuity = navier_stokes_residual(
        velocity,
        pressure,
        x,
        t,
        FluidParameters(kinematic_viscosity=viscosity),
    )

    assert momentum.abs().max().item() < 1.0e-10
    assert continuity.abs().max().item() < 1.0e-10


def test_diffusing_temperature_and_scalar_residuals() -> None:
    torch.set_default_dtype(torch.float64)
    sample_count = 64
    diffusivity = 2.0e-2

    x = (2.0 * math.pi * torch.rand(sample_count, 2)).requires_grad_()
    t = torch.rand(sample_count, 1, requires_grad=True)
    decay = torch.exp(-2.0 * diffusivity * t[:, 0])
    field = torch.sin(x[:, 0]) * torch.sin(x[:, 1]) * decay
    velocity = torch.zeros(sample_count, 2, dtype=x.dtype)

    parameters = FluidParameters(
        density=1.0,
        heat_capacity=1.0,
        thermal_conductivity=diffusivity,
        scalar_diffusivity=diffusivity,
    )

    thermal = temperature_residual(field, velocity, x, t, parameters)
    scalar = passive_scalar_residual(field, velocity, x, t, parameters)

    assert thermal.abs().max().item() < 1.0e-10
    assert scalar.abs().max().item() < 1.0e-10


def test_2d_vortex_stretching_is_zero() -> None:
    grid_size = 64
    domain_length = 2.0 * math.pi
    spacing_value = domain_length / grid_size
    axis = torch.arange(grid_size, dtype=torch.float64) * spacing_value
    x, y = torch.meshgrid(axis, axis, indexing="ij")
    velocity = torch.stack(
        (
            torch.sin(x) * torch.cos(y),
            -torch.cos(x) * torch.sin(y),
        ),
        dim=-1,
    )

    omega = vorticity(velocity, (spacing_value, spacing_value))
    stretching, diffusion = vorticity_balance_terms(
        velocity,
        (spacing_value, spacing_value),
        viscosity=1.0e-3,
    )
    metrics = compute_metrics(
        velocity,
        (spacing_value, spacing_value),
        viscosity=1.0e-3,
    )

    assert omega.abs().max().item() > 1.9
    assert torch.count_nonzero(stretching).item() == 0
    assert diffusion.abs().max().item() > 0
    assert metrics.vortex_stretching_rate == 0.0
    assert metrics.regulation_ratio == 0.0


def test_marked_scalar_preservation_metrics() -> None:
    initial = torch.tensor([[0.0, 1.0], [2.0, 0.0]], dtype=torch.float64)
    unchanged = initial.clone()
    depleted = initial * 0.5

    perfect = compute_marked_scalar_metrics(initial, unchanged)
    assert perfect.mass_fidelity == 1.0
    assert perfect.soft_overlap > 0.999999

    assert mass_fidelity(initial, depleted).item() == pytest.approx(0.5)
    assert 0.0 < soft_overlap(initial, depleted).item() < 1.0
