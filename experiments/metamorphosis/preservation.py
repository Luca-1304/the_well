"""Purpose-relative preservation metrics for a transformed test substance X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


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


def weighted_preservation(
    scores: PreservationScore,
    weights: Mapping[str, float],
) -> float:
    """Return a secondary weighted score without replacing the minimum rule.

    The minimum remains the critical survival test. This average is useful for
    ranking two successful runs after both have cleared the survival threshold.
    """
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
