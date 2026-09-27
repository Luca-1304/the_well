"""Simulation-level robustness and recovery sweeps for Metamorphosis."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Sequence

from .safety import minimum_flip_margin, minimum_recovery_cost
from .solver3d import (
    PeriodicSpectralNavierStokes3D,
    SimulationRecord,
    SpectralSimulationConfig,
)


@dataclass(frozen=True)
class OutcomeSignature:
    trusted: bool
    contained: bool
    isolated: bool


@dataclass(frozen=True)
class AmplitudeRobustnessResult:
    perturbation: float
    amplitude: float
    outcome: OutcomeSignature
    peak_velocity_gradient: float
    peak_vorticity: float


@dataclass(frozen=True)
class RecoveryTrial:
    max_control_force: float
    recovered: bool
    integrated_control_effort: float
    peak_velocity_gradient: float
    final_safety_mode: str


def outcome_signature(records: Sequence[SimulationRecord]) -> OutcomeSignature:
    if not records:
        return OutcomeSignature(
            trusted=False,
            contained=False,
            isolated=True,
        )
    return OutcomeSignature(
        trusted=all(record.trusted_prediction for record in records),
        contained=not any(record.containment_failed for record in records),
        isolated=any(record.safety_mode == "isolate" for record in records),
    )


def amplitude_robustness_sweep(
    config: SpectralSimulationConfig,
    perturbations: Sequence[float],
    *,
    nominal_amplitude: float = 1.0,
) -> tuple[list[AmplitudeRobustnessResult], float]:
    """Find the smallest tested initial-amplitude perturbation that flips outcome."""
    if not perturbations:
        raise ValueError("perturbations cannot be empty")
    if nominal_amplitude <= 0 or not math.isfinite(nominal_amplitude):
        raise ValueError("nominal_amplitude must be finite and positive")

    solver = PeriodicSpectralNavierStokes3D(config)
    _, nominal_records = solver.run(amplitude=nominal_amplitude)
    nominal_outcome = outcome_signature(nominal_records)

    results: list[AmplitudeRobustnessResult] = []
    norms: list[float] = []
    changed: list[bool] = []

    for perturbation in perturbations:
        if not math.isfinite(perturbation):
            raise ValueError("perturbations must be finite")
        amplitude = nominal_amplitude * (1.0 + perturbation)
        if amplitude <= 0:
            raise ValueError("perturbation produces a non-positive amplitude")

        _, records = PeriodicSpectralNavierStokes3D(config).run(amplitude=amplitude)
        outcome = outcome_signature(records)
        results.append(
            AmplitudeRobustnessResult(
                perturbation=perturbation,
                amplitude=amplitude,
                outcome=outcome,
                peak_velocity_gradient=max(
                    record.max_velocity_gradient for record in records
                ),
                peak_vorticity=max(record.max_vorticity for record in records),
            )
        )
        norms.append(abs(perturbation))
        changed.append(outcome != nominal_outcome)

    return results, minimum_flip_margin(norms, changed)


def recovery_sweep(
    config: SpectralSimulationConfig,
    max_control_forces: Sequence[float],
    *,
    max_velocity_gradient_limit: float,
) -> tuple[list[RecoveryTrial], float]:
    """Measure least integrated effort meeting a declared recovery criterion."""
    if not max_control_forces:
        raise ValueError("max_control_forces cannot be empty")
    if max_velocity_gradient_limit <= 0 or not math.isfinite(
        max_velocity_gradient_limit
    ):
        raise ValueError("max_velocity_gradient_limit must be finite and positive")

    trials: list[RecoveryTrial] = []
    costs: list[float] = []
    recovered_flags: list[bool] = []

    for force_limit in max_control_forces:
        if force_limit <= 0 or not math.isfinite(force_limit):
            raise ValueError("control force limits must be finite and positive")

        controller = replace(
            config.controller,
            max_control_force=force_limit,
        )
        trial_config = replace(
            config,
            controller_enabled=True,
            controller=controller,
        )
        _, records = PeriodicSpectralNavierStokes3D(trial_config).run()
        peak_gradient = max(record.max_velocity_gradient for record in records)
        recovered = (
            peak_gradient <= max_velocity_gradient_limit
            and not any(record.watchdog_triggered for record in records)
            and not any(record.containment_failed for record in records)
            and records[-1].safety_mode not in ("emergency", "isolate")
        )
        integrated_effort = sum(
            record.control_effort * record.time_step for record in records
        )
        trials.append(
            RecoveryTrial(
                max_control_force=force_limit,
                recovered=recovered,
                integrated_control_effort=integrated_effort,
                peak_velocity_gradient=peak_gradient,
                final_safety_mode=records[-1].safety_mode,
            )
        )
        costs.append(integrated_effort)
        recovered_flags.append(recovered)

    return trials, minimum_recovery_cost(costs, recovered_flags)
