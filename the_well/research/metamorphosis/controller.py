"""Baseline controllers for concentration-triggered flow experiments."""

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


def vorticity_weighted_damping_force(
    velocity: Tensor,
    vorticity_field: Tensor,
    config: ControllerConfig,
) -> Tensor:
    """Return a bounded damping baseline weighted by local vorticity.

    This force opposes local velocity where vorticity is strongest. It is a
    control baseline, not yet a derived redistribution law: a lower peak could
    result from suppressing the flow rather than spreading concentration while
    preserving continued motion.
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

    raw_force = (
        -config.proportional_gain * error * local_weight.unsqueeze(-1) * velocity
    )
    magnitude = torch.linalg.vector_norm(raw_force, dim=-1, keepdim=True)
    scale = torch.clamp(
        config.max_control_force / (magnitude + config.epsilon),
        max=1.0,
    )
    return raw_force * scale


def adaptive_redistribution_force(
    velocity: Tensor,
    vorticity_field: Tensor,
    config: ControllerConfig,
) -> Tensor:
    """Compatibility alias for the initial damping baseline.

    Future pressure, boundary, thermal, and counter-vorticity controllers should
    implement actual redistribution rather than relying on this alias.
    """
    return vorticity_weighted_damping_force(velocity, vorticity_field, config)


def regulation_ratio(
    concentration_rate: Tensor,
    redistribution_rate: Tensor,
    epsilon: float = 1.0e-8,
) -> Tensor:
    """Return a dimensionless ratio when both inputs share physical units."""
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    if torch.any(concentration_rate < 0) or torch.any(redistribution_rate < 0):
        raise ValueError("rates must be non-negative magnitudes")
    return concentration_rate / (redistribution_rate + epsilon)
