"""Purpose-relative preservation metrics for a transformed test substance X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
from torch import Tensor


@dataclass(frozen=True)
class PreservationScore:
    essential_matter: float
    composition: float
    structure: float
    information: float
    function: float

    def __post_init__(self) -> None:
        for name, value in self.as_dict().items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    def as_dict(self) -> dict[str, float]:
        return {
            "essential_matter": self.essential_matter,
            "composition": self.composition,
            "structure": self.structure,
            "information": self.information,
            "function": self.function,
        }

    @property
    def existence_score(self) -> float:
        """The weakest essential property sets the preservation floor."""
        return min(self.as_dict().values())

    def survives(self, threshold: float) -> bool:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        return self.existence_score >= threshold


@dataclass(frozen=True)
class MarkedScalarMetrics:
    mass_fidelity: float
    soft_overlap: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.mass_fidelity <= 1.0:
            raise ValueError("mass_fidelity must be between 0 and 1")
        if not 0.0 <= self.soft_overlap <= 1.0:
            raise ValueError("soft_overlap must be between 0 and 1")


def weighted_preservation(
    scores: PreservationScore,
    weights: Mapping[str, float],
) -> float:
    """Return a secondary weighted score without replacing the minimum rule."""
    values = scores.as_dict()
    unknown = set(weights) - set(values)
    if unknown:
        raise ValueError(f"unknown preservation fields: {sorted(unknown)}")
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("weights must have a positive total")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("weights cannot be negative")
    return sum(values[name] * weight for name, weight in weights.items()) / total_weight


def marked_scalar_mass(field: Tensor, cell_volume: float = 1.0) -> Tensor:
    """Return non-negative integrated marked-scalar mass."""
    if cell_volume <= 0:
        raise ValueError("cell_volume must be positive")
    return field.clamp_min(0).sum() * cell_volume


def mass_fidelity(
    initial: Tensor,
    current: Tensor,
    cell_volume: float = 1.0,
    epsilon: float = 1.0e-12,
) -> Tensor:
    """Return 1 for exact mass retention and decrease symmetrically with error."""
    if initial.shape != current.shape:
        raise ValueError("initial and current fields must have the same shape")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")

    initial_mass = marked_scalar_mass(initial, cell_volume)
    current_mass = marked_scalar_mass(current, cell_volume)
    relative_error = (current_mass - initial_mass).abs() / (
        initial_mass.abs() + epsilon
    )
    return torch.clamp(1.0 - relative_error, min=0.0, max=1.0)


def soft_overlap(
    reference: Tensor,
    candidate: Tensor,
    epsilon: float = 1.0e-12,
) -> Tensor:
    """Continuous intersection-over-union for aligned non-negative fields.

    This measures spatial structure in the current coordinate frame. A later
    Lagrangian or alignment-aware metric is required when translation itself
    should not count as loss of identity.
    """
    if reference.shape != candidate.shape:
        raise ValueError("reference and candidate fields must have the same shape")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")

    reference = reference.clamp_min(0)
    candidate = candidate.clamp_min(0)
    intersection = torch.minimum(reference, candidate).sum()
    union = torch.maximum(reference, candidate).sum()
    return intersection / (union + epsilon)


def compute_marked_scalar_metrics(
    initial: Tensor,
    current: Tensor,
    *,
    cell_volume: float = 1.0,
) -> MarkedScalarMetrics:
    return MarkedScalarMetrics(
        mass_fidelity=float(
            mass_fidelity(initial, current, cell_volume).detach().cpu()
        ),
        soft_overlap=float(soft_overlap(initial, current).detach().cpu()),
    )
