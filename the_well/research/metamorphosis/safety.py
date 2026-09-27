"""Safety, robustness, and model-credibility utilities for Metamorphosis.

The functions in this module do not prove physical correctness. They make
uncertainty, model mismatch, containment, recovery authority, and human-input
provenance explicit so a loss of credibility reduces permitted control
authority rather than merely changing a displayed confidence score.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Sequence

from torch import Tensor


class OperationalMode(str, Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    SAFE = "safe"
    EMERGENCY = "emergency"
    ISOLATE = "isolate"


class BoundaryMode(str, Enum):
    CLOSED_STRONG = "closed_strong"
    WEAK_CONTAINMENT = "weak_containment"
    OPEN = "open"


@dataclass(frozen=True)
class ValidityGate:
    units_valid: bool
    domain_valid: bool
    inputs_complete: bool
    initial_conditions_valid: bool
    boundary_conditions_valid: bool
    identifiable: bool

    @property
    def failures(self) -> tuple[str, ...]:
        checks = {
            "units": self.units_valid,
            "domain": self.domain_valid,
            "inputs": self.inputs_complete,
            "initial_conditions": self.initial_conditions_valid,
            "boundary_conditions": self.boundary_conditions_valid,
            "identifiability": self.identifiable,
        }
        return tuple(name for name, passed in checks.items() if not passed)

    @property
    def passes(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class SafetyThresholds:
    restricted: float = 0.20
    safe: float = 0.40
    emergency: float = 0.70
    isolate: float = 0.90

    def validate(self) -> None:
        values = (self.restricted, self.safe, self.emergency, self.isolate)
        if not all(0.0 <= value <= 1.0 for value in values):
            raise ValueError("safety thresholds must lie between 0 and 1")
        if not (self.restricted < self.safe < self.emergency < self.isolate):
            raise ValueError("safety thresholds must be strictly increasing")


@dataclass(frozen=True)
class RiskVector:
    physics: float
    numerical: float
    uncertainty: float
    control: float
    external: float
    mismatch: float

    def __post_init__(self) -> None:
        for name, value in self.as_dict().items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} risk must be between 0 and 1")

    def as_dict(self) -> dict[str, float]:
        return {
            "physics": self.physics,
            "numerical": self.numerical,
            "uncertainty": self.uncertainty,
            "control": self.control,
            "external": self.external,
            "mismatch": self.mismatch,
        }

    @property
    def maximum(self) -> float:
        return max(self.as_dict().values())


@dataclass(frozen=True)
class VerificationState:
    pde_residual: float
    divergence_residual: float
    energy_residual: float
    solver_discrepancy: float
    convergence_error: float
    observation_mismatch: float
    uncertainty: float
    domain_distance: float

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class VerificationScales:
    pde_residual: float
    divergence_residual: float
    energy_residual: float
    solver_discrepancy: float
    convergence_error: float
    observation_mismatch: float
    uncertainty: float
    domain_distance: float

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} scale must be finite and positive")


@dataclass(frozen=True)
class SafetyDecision:
    mode: OperationalMode
    authority_scale: float
    trusted_prediction: bool
    model_mismatch: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class BoundaryState:
    mode: BoundaryMode
    load: float
    capacity: float
    permeability: float
    coupling: float
    environmental_strength: float
    breachable: bool = True

    def __post_init__(self) -> None:
        if self.load < 0 or not math.isfinite(self.load):
            raise ValueError("boundary load must be finite and non-negative")
        if self.capacity <= 0 or not math.isfinite(self.capacity):
            raise ValueError("boundary capacity must be finite and positive")
        if not 0.0 <= self.permeability <= 1.0:
            raise ValueError("permeability must be between 0 and 1")
        if not 0.0 <= self.coupling <= 1.0:
            raise ValueError("coupling must be between 0 and 1")
        if self.environmental_strength < 0 or not math.isfinite(
            self.environmental_strength
        ):
            raise ValueError("environmental_strength must be finite and non-negative")
        if self.mode is BoundaryMode.CLOSED_STRONG and self.permeability != 0.0:
            raise ValueError("closed_strong boundaries require zero permeability")

    @property
    def containment_margin(self) -> float:
        return self.capacity - self.load

    @property
    def containment_failed(self) -> bool:
        return self.breachable and self.load >= self.capacity

    @property
    def environmental_influence(self) -> float:
        return self.environmental_strength * self.permeability * self.coupling


@dataclass(frozen=True)
class OverpoweringMetrics:
    dominance_ratio: float
    accumulated_exceedance: float
    timescale_ratio: float
    effective_disturbance: float
    cascade_gain: float
    recoverability_distance: float

    @property
    def disturbance_dominates(self) -> bool:
        return self.dominance_ratio > 1.0

    @property
    def response_is_slower(self) -> bool:
        return self.timescale_ratio > 1.0

    @property
    def cascade_is_amplifying(self) -> bool:
        return self.cascade_gain > 1.0


@dataclass(frozen=True)
class ScalarInputRecord:
    name: str
    value: float
    unit: str
    uncertainty: float
    source: str

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("input name cannot be empty")
        if not math.isfinite(self.value):
            raise ValueError("input value must be finite")
        if not self.unit.strip():
            raise ValueError("input unit cannot be empty")
        if self.uncertainty < 0 or not math.isfinite(self.uncertainty):
            raise ValueError("input uncertainty must be finite and non-negative")
        if not self.source.strip():
            raise ValueError("input source cannot be empty")


@dataclass(frozen=True)
class RunManifest:
    code_version: str
    model_version: str
    initial_condition_id: str
    boundary_condition: str
    solver: str
    precision: str
    grid_shape: tuple[int, ...]
    time_step: float
    random_seed: int
    configuration_fingerprint: str

    def validate(self) -> None:
        text_fields = (
            self.code_version,
            self.model_version,
            self.initial_condition_id,
            self.boundary_condition,
            self.solver,
            self.precision,
            self.configuration_fingerprint,
        )
        if any(not value.strip() for value in text_fields):
            raise ValueError("manifest text fields cannot be empty")
        if not self.grid_shape or any(size <= 0 for size in self.grid_shape):
            raise ValueError("grid_shape must contain positive sizes")
        if self.time_step <= 0 or not math.isfinite(self.time_step):
            raise ValueError("time_step must be finite and positive")


def normalized_ratio(value: float, scale: float) -> float:
    """Map a non-negative magnitude to [0, 1) using an explicit scale."""
    if value < 0 or not math.isfinite(value):
        raise ValueError("value must be finite and non-negative")
    if scale <= 0 or not math.isfinite(scale):
        raise ValueError("scale must be finite and positive")
    return value / (value + scale)


def normalized_driver_strength(force_norm: float, reference_force: float) -> float:
    """Return a dimensionless driver strength with a fixed reference scale."""
    if force_norm < 0 or not math.isfinite(force_norm):
        raise ValueError("force_norm must be finite and non-negative")
    if reference_force <= 0 or not math.isfinite(reference_force):
        raise ValueError("reference_force must be finite and positive")
    return force_norm / reference_force


def risk_from_verification(
    state: VerificationState,
    scales: VerificationScales,
    *,
    control_risk: float = 0.0,
    external_risk: float = 0.0,
) -> RiskVector:
    for name, value in {
        "control_risk": control_risk,
        "external_risk": external_risk,
    }.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")

    physics = max(
        normalized_ratio(state.pde_residual, scales.pde_residual),
        normalized_ratio(state.divergence_residual, scales.divergence_residual),
        normalized_ratio(state.energy_residual, scales.energy_residual),
    )
    numerical = max(
        normalized_ratio(state.solver_discrepancy, scales.solver_discrepancy),
        normalized_ratio(state.convergence_error, scales.convergence_error),
    )
    uncertainty = normalized_ratio(state.uncertainty, scales.uncertainty)
    mismatch = max(
        normalized_ratio(
            state.observation_mismatch,
            scales.observation_mismatch,
        ),
        normalized_ratio(state.domain_distance, scales.domain_distance),
    )
    return RiskVector(
        physics=physics,
        numerical=numerical,
        uncertainty=uncertainty,
        control=control_risk,
        external=external_risk,
        mismatch=mismatch,
    )


def confidence_from_risk(
    risk: RiskVector,
    weights: Mapping[str, float] | None = None,
) -> float:
    """Return a conservative confidence score that falls as risk rises."""
    values = risk.as_dict()
    if weights is None:
        weights = {name: 1.0 for name in values}

    unknown = set(weights) - set(values)
    if unknown:
        raise ValueError(f"unknown risk fields: {sorted(unknown)}")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("risk weights cannot be negative")
    if sum(weights.values()) <= 0:
        raise ValueError("risk weights must have a positive total")

    weighted_risk = sum(values[name] * weights.get(name, 0.0) for name in values)
    return math.exp(-weighted_risk)


def mode_for_risk(
    maximum_risk: float,
    thresholds: SafetyThresholds = SafetyThresholds(),
) -> OperationalMode:
    thresholds.validate()
    if not 0.0 <= maximum_risk <= 1.0:
        raise ValueError("maximum_risk must be between 0 and 1")
    if maximum_risk >= thresholds.isolate:
        return OperationalMode.ISOLATE
    if maximum_risk >= thresholds.emergency:
        return OperationalMode.EMERGENCY
    if maximum_risk >= thresholds.safe:
        return OperationalMode.SAFE
    if maximum_risk >= thresholds.restricted:
        return OperationalMode.RESTRICTED
    return OperationalMode.NORMAL


def authority_for_mode(mode: OperationalMode) -> float:
    return {
        OperationalMode.NORMAL: 1.0,
        OperationalMode.RESTRICTED: 0.5,
        OperationalMode.SAFE: 0.25,
        OperationalMode.EMERGENCY: 0.10,
        OperationalMode.ISOLATE: 0.0,
    }[mode]


def evaluate_safety(
    risk: RiskVector,
    *,
    thresholds: SafetyThresholds = SafetyThresholds(),
    model_mismatch: bool = False,
) -> SafetyDecision:
    mode = mode_for_risk(risk.maximum, thresholds)
    order = list(OperationalMode)
    if model_mismatch and order.index(mode) < order.index(OperationalMode.SAFE):
        mode = OperationalMode.SAFE

    maximum = risk.maximum
    reasons = tuple(
        name for name, value in risk.as_dict().items() if value == maximum and value > 0
    )
    if model_mismatch:
        reasons = reasons + ("model_mismatch",)

    return SafetyDecision(
        mode=mode,
        authority_scale=authority_for_mode(mode),
        trusted_prediction=(
            not model_mismatch
            and mode in (OperationalMode.NORMAL, OperationalMode.RESTRICTED)
        ),
        model_mismatch=model_mismatch,
        reasons=reasons,
    )


def detect_model_mismatch(
    state: VerificationState,
    scales: VerificationScales,
    *,
    threshold: float = 0.5,
) -> bool:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    observation_risk = normalized_ratio(
        state.observation_mismatch,
        scales.observation_mismatch,
    )
    domain_risk = normalized_ratio(state.domain_distance, scales.domain_distance)
    physics_risk = max(
        normalized_ratio(state.pde_residual, scales.pde_residual),
        normalized_ratio(state.divergence_residual, scales.divergence_residual),
    )
    return max(observation_risk, domain_risk, physics_risk) >= threshold


def authority_limited_force(force: Tensor, authority_scale: float) -> Tensor:
    if not 0.0 <= authority_scale <= 1.0:
        raise ValueError("authority_scale must be between 0 and 1")
    return force * authority_scale


def overpowering_metrics(
    *,
    disturbance: float,
    restoring: float,
    exceedance_duration: float,
    response_time: float,
    disturbance_time: float,
    concentration_factor: float = 1.0,
    geometry_gain: float = 1.0,
    coupling: float = 1.0,
    cascade_gain: float = 1.0,
    recoverability_distance: float = 0.0,
) -> OverpoweringMetrics:
    """Summarise a dimensionless overpowering-event scenario.

    concentration_factor, geometry_gain, coupling, and cascade_gain are
    dimensionless modifiers supplied by the domain model. This function does
    not infer them from raw physical measurements.
    """
    values = {
        "disturbance": disturbance,
        "restoring": restoring,
        "exceedance_duration": exceedance_duration,
        "response_time": response_time,
        "disturbance_time": disturbance_time,
        "concentration_factor": concentration_factor,
        "geometry_gain": geometry_gain,
        "coupling": coupling,
        "cascade_gain": cascade_gain,
        "recoverability_distance": recoverability_distance,
    }
    for name, value in values.items():
        if value < 0 or not math.isfinite(value):
            raise ValueError(f"{name} must be finite and non-negative")
    if disturbance_time <= 0:
        raise ValueError("disturbance_time must be positive")

    effective_disturbance = (
        disturbance * concentration_factor * geometry_gain * coupling
    )
    if restoring == 0.0:
        dominance_ratio = 0.0 if effective_disturbance == 0.0 else float("inf")
    else:
        dominance_ratio = effective_disturbance / restoring

    if math.isinf(dominance_ratio):
        accumulated_exceedance = float("inf") if exceedance_duration > 0.0 else 0.0
    else:
        accumulated_exceedance = max(dominance_ratio - 1.0, 0.0) * exceedance_duration
    timescale_ratio = response_time / disturbance_time
    return OverpoweringMetrics(
        dominance_ratio=dominance_ratio,
        accumulated_exceedance=accumulated_exceedance,
        timescale_ratio=timescale_ratio,
        effective_disturbance=effective_disturbance,
        cascade_gain=cascade_gain,
        recoverability_distance=recoverability_distance,
    )


def minimum_flip_margin(
    perturbation_norms: Sequence[float],
    outcome_changed: Sequence[bool],
) -> float:
    """Return the smallest tested perturbation that changes the outcome."""
    if len(perturbation_norms) != len(outcome_changed):
        raise ValueError("perturbation_norms and outcome_changed must align")
    if any(value < 0 or not math.isfinite(value) for value in perturbation_norms):
        raise ValueError("perturbation norms must be finite and non-negative")
    candidates = [
        value for value, changed in zip(perturbation_norms, outcome_changed) if changed
    ]
    return min(candidates) if candidates else float("inf")


def minimum_recovery_cost(
    recovery_costs: Sequence[float],
    recovered: Sequence[bool],
) -> float:
    """Return the least tested intervention cost that restores viability."""
    if len(recovery_costs) != len(recovered):
        raise ValueError("recovery_costs and recovered must align")
    if any(value < 0 or not math.isfinite(value) for value in recovery_costs):
        raise ValueError("recovery costs must be finite and non-negative")
    candidates = [value for value, ok in zip(recovery_costs, recovered) if ok]
    return min(candidates) if candidates else float("inf")


def configuration_fingerprint(configuration: Mapping[str, object]) -> str:
    """Return a stable SHA-256 fingerprint for a JSON-serialisable configuration."""
    encoded = json.dumps(
        configuration,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_validity(gate: ValidityGate) -> None:
    """Block execution when any pre-run validity requirement is unresolved."""
    if not gate.passes:
        failures = ", ".join(gate.failures)
        raise ValueError(f"validity gate failed: {failures}")


def validate_input_records(records: Sequence[ScalarInputRecord]) -> None:
    """Validate provenance-bearing scalar inputs and reject duplicate names."""
    seen: set[str] = set()
    for record in records:
        record.validate()
        if record.name in seen:
            raise ValueError(f"duplicate input name: {record.name}")
        seen.add(record.name)
