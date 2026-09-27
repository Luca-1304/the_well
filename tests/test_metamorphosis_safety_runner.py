from __future__ import annotations

from the_well.research.metamorphosis.run_safety_stress import run_stress_matrix


def test_safety_stress_runner_escalates_known_failures() -> None:
    result = run_stress_matrix()
    cases = {case["name"]: case for case in result["verification_cases"]}

    assert cases["nominal"]["mode"] == "normal"
    assert cases["nominal"]["trusted_prediction"]

    observation = cases["observation_failure"]
    assert observation["model_mismatch"]
    assert not observation["trusted_prediction"]
    assert observation["authority_scale"] <= 0.25

    physics = cases["physics_failure"]
    assert physics["mode"] == "isolate"
    assert physics["authority_scale"] == 0.0

    boundaries = {case["mode"]: case for case in result["boundary_cases"]}
    assert not boundaries["closed_strong"]["containment_failed"]
    assert boundaries["closed_strong"]["environmental_influence"] == 0.0
    assert boundaries["weak_containment"]["containment_failed"]
    assert boundaries["open"]["environmental_influence"] > 0.0
