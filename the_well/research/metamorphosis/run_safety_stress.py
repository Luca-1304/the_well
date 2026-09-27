"""Run deterministic safety-shell stress scenarios.

This runner exercises credibility loss and containment logic independently of a
full Navier–Stokes time stepper. It is a software/safety contract check, not a
physical validation experiment.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from .safety import (
    BoundaryMode,
    BoundaryState,
    VerificationScales,
    VerificationState,
    detect_model_mismatch,
    evaluate_safety,
    overpowering_metrics,
    risk_from_verification,
)


def default_scales() -> VerificationScales:
    return VerificationScales(
        pde_residual=1.0,
        divergence_residual=1.0,
        energy_residual=1.0,
        solver_discrepancy=1.0,
        convergence_error=1.0,
        observation_mismatch=1.0,
        uncertainty=1.0,
        domain_distance=1.0,
    )


def evaluate_case(
    name: str,
    state: VerificationState,
    *,
    control_risk: float = 0.0,
    external_risk: float = 0.0,
) -> dict[str, object]:
    scales = default_scales()
    risk = risk_from_verification(
        state,
        scales,
        control_risk=control_risk,
        external_risk=external_risk,
    )
    mismatch = detect_model_mismatch(state, scales)
    decision = evaluate_safety(risk, model_mismatch=mismatch)
    return {
        "name": name,
        "risk": risk.as_dict(),
        "model_mismatch": mismatch,
        "mode": decision.mode.value,
        "authority_scale": decision.authority_scale,
        "trusted_prediction": decision.trusted_prediction,
        "reasons": list(decision.reasons),
    }


def run_stress_matrix() -> dict[str, object]:
    nominal = VerificationState(
        pde_residual=1.0e-3,
        divergence_residual=1.0e-4,
        energy_residual=1.0e-3,
        solver_discrepancy=1.0e-3,
        convergence_error=1.0e-3,
        observation_mismatch=1.0e-3,
        uncertainty=1.0e-2,
        domain_distance=0.0,
    )
    observation_failure = VerificationState(
        pde_residual=1.0e-3,
        divergence_residual=1.0e-4,
        energy_residual=1.0e-3,
        solver_discrepancy=1.0e-3,
        convergence_error=1.0e-3,
        observation_mismatch=2.0,
        uncertainty=0.2,
        domain_distance=0.0,
    )
    physics_failure = VerificationState(
        pde_residual=10.0,
        divergence_residual=2.0,
        energy_residual=4.0,
        solver_discrepancy=0.1,
        convergence_error=0.2,
        observation_mismatch=0.0,
        uncertainty=0.1,
        domain_distance=0.0,
    )

    closed = BoundaryState(
        mode=BoundaryMode.CLOSED_STRONG,
        load=4.0,
        capacity=10.0,
        permeability=0.0,
        coupling=1.0,
        environmental_strength=100.0,
    )
    weak = BoundaryState(
        mode=BoundaryMode.WEAK_CONTAINMENT,
        load=12.0,
        capacity=10.0,
        permeability=0.5,
        coupling=0.4,
        environmental_strength=20.0,
    )
    open_boundary = BoundaryState(
        mode=BoundaryMode.OPEN,
        load=2.0,
        capacity=10.0,
        permeability=1.0,
        coupling=0.8,
        environmental_strength=20.0,
    )

    overpowering = overpowering_metrics(
        disturbance=2.0,
        restoring=1.0,
        exceedance_duration=3.0,
        response_time=2.0,
        disturbance_time=1.0,
        concentration_factor=2.0,
        geometry_gain=1.5,
        coupling=0.5,
        cascade_gain=1.2,
        recoverability_distance=0.1,
    )

    return {
        "verification_cases": [
            evaluate_case("nominal", nominal),
            evaluate_case("observation_failure", observation_failure),
            evaluate_case("physics_failure", physics_failure),
        ],
        "boundary_cases": [
            {
                "mode": boundary.mode.value,
                "containment_margin": boundary.containment_margin,
                "containment_failed": boundary.containment_failed,
                "environmental_influence": boundary.environmental_influence,
            }
            for boundary in (closed, weak, open_boundary)
        ],
        "overpowering_case": asdict(overpowering),
    }


def main() -> None:
    print(json.dumps(run_stress_matrix(), indent=2))


if __name__ == "__main__":
    main()
