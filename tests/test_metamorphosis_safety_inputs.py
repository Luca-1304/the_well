from __future__ import annotations

import math

import pytest
import torch

from the_well.research.metamorphosis.safety import (
    RiskVector,
    RunManifest,
    ScalarInputRecord,
    ValidityGate,
    authority_limited_force,
    confidence_from_risk,
    normalized_driver_strength,
    require_validity,
    validate_input_records,
)


def test_require_validity_blocks_failed_gate() -> None:
    gate = ValidityGate(
        units_valid=True,
        domain_valid=True,
        inputs_complete=True,
        initial_conditions_valid=True,
        boundary_conditions_valid=False,
        identifiable=True,
    )
    with pytest.raises(ValueError, match="boundary_conditions"):
        require_validity(gate)


def test_input_records_require_units_source_and_unique_names() -> None:
    records = [
        ScalarInputRecord(
            name="viscosity",
            value=1.0e-3,
            unit="m^2/s",
            uncertainty=1.0e-5,
            source="calibrated_input",
        ),
        ScalarInputRecord(
            name="density",
            value=1.0,
            unit="kg/m^3",
            uncertainty=1.0e-3,
            source="calibrated_input",
        ),
    ]
    validate_input_records(records)

    duplicate = records + [
        ScalarInputRecord(
            name="viscosity",
            value=2.0e-3,
            unit="m^2/s",
            uncertainty=1.0e-5,
            source="second_source",
        )
    ]
    with pytest.raises(ValueError, match="duplicate input name"):
        validate_input_records(duplicate)

    with pytest.raises(ValueError, match="unit"):
        ScalarInputRecord(
            name="bad",
            value=1.0,
            unit="",
            uncertainty=0.0,
            source="test",
        ).validate()


def test_run_manifest_rejects_invalid_time_step() -> None:
    manifest = RunManifest(
        code_version="abc123",
        model_version="safety-v1",
        initial_condition_id="tg-2d",
        boundary_condition="periodic",
        solver="analytic",
        precision="float64",
        grid_shape=(64, 64),
        time_step=0.0,
        random_seed=0,
        configuration_fingerprint="deadbeef",
    )
    with pytest.raises(ValueError, match="time_step"):
        manifest.validate()


def test_driver_normalisation_requires_fixed_reference() -> None:
    assert normalized_driver_strength(10.0, 2.0) == pytest.approx(5.0)
    with pytest.raises(ValueError, match="reference_force"):
        normalized_driver_strength(10.0, 0.0)


def test_confidence_falls_when_risk_increases() -> None:
    low = RiskVector(
        physics=0.01,
        numerical=0.01,
        uncertainty=0.01,
        control=0.01,
        external=0.01,
        mismatch=0.01,
    )
    high = RiskVector(
        physics=0.8,
        numerical=0.8,
        uncertainty=0.8,
        control=0.8,
        external=0.8,
        mismatch=0.8,
    )
    low_confidence = confidence_from_risk(low)
    high_confidence = confidence_from_risk(high)

    assert 0.0 < high_confidence < low_confidence <= 1.0


def test_authority_limiter_is_monotonic() -> None:
    force = torch.tensor([3.0, 4.0], dtype=torch.float64)
    full = authority_limited_force(force, 1.0)
    restricted = authority_limited_force(force, 0.25)
    isolated = authority_limited_force(force, 0.0)

    assert torch.linalg.vector_norm(full).item() == pytest.approx(5.0)
    assert torch.linalg.vector_norm(restricted).item() == pytest.approx(1.25)
    assert torch.count_nonzero(isolated).item() == 0


def test_input_record_rejects_nonfinite_uncertainty() -> None:
    record = ScalarInputRecord(
        name="temperature",
        value=300.0,
        unit="K",
        uncertainty=math.inf,
        source="sensor",
    )
    with pytest.raises(ValueError, match="uncertainty"):
        record.validate()
