"""Initial negative-feedback controller for concentration-driven redistribution."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor


@dataclass(frozen=True)
class ControllerConfig:
    safe_vorticity: float
    proportional_gain: float
    max_control_force: float
    epsilon: float = 1.0e-8

    def validate(self) -> None:
        if self.safe_vorticity < 0:
            raise ValueError("safe_vorticity cannot be negative")
        if self.proportional_gain < 0:
            raise ValueError("proportional_gain cannot be negative")
        if self.max_control_force <= 0:
            raise ValueError("max_control_force must be positive")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive")


def concentration_error(max_vorticity: Tensor, safe_vorticity: float) -> Tensor:
    """Only concentration above the safe target activates the controller."""
    return torch.clamp(max_vorticity - safe_vorticity, min=0.0)


def adaptive_redistribution_force(
    velocity: Tensor,
    vorticity_field: Tensor,
    config: ControllerConfig,
) -> Tensor:
    """Return a bounded first-pass force opposing local rotational concentration.

    This is a test controller, not a derived optimal law.  It damps velocity in
    proportion to excess local vorticity while preserving the field shape for
    later comparison with pressure, thermal, boundary, and magnetic controls.
    """
    config.validate()

    if vorticity_field.ndim == velocity.ndim - 1:
        omega_magnitude = vorticity_field.abs()
    elif vorticity_field.shape[-1] in (2, 3):
        omega_magnitude = torch.linalg.vector_norm(vorticity_field, dim=-1)
    else:
        raise ValueError("unsupported vorticity field shape")

    max_vorticity = omega_magnitude.amax()
    error = concentration_error(max_vorticity, config.safe_vorticity)

    local_weight = omega_magnitude / (max_vorticity + config.epsilon)
    raw_force = -config.proportional_gain * error * local_weight.unsqueeze(-1) * velocity

    magnitude = torch.linalg.vector_norm(raw_force, dim=-1, keepdim=True)
    scale = torch.clamp(config.max_control_force / (magnitude + config.epsilon), max=1.0)
    return raw_force * scale


def regulation_ratio(
    concentration_rate: Tensor,
    redistribution_rate: Tensor,
    epsilon: float = 1.0e-8,
) -> Tensor:
    """Diagnostic R = concentration / redistribution; desired R <= 1."""
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    return concentration_rate / (redistribution_rate + epsilon)
