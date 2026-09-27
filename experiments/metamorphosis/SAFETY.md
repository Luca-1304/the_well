# Metamorphosis Safety and Robustness Contract

This document hardens the 0→1→2→3→4 research architecture against model error, numerical error, environmental surprise, control failure, and ordinary human configuration mistakes.

## Canonical architecture

0. **Validate** — units, active physical regime, inputs, initial conditions, boundary conditions, observability/identifiability, and provenance.
1. **Driver** — identify and normalise the physical drivers.
2. **Interaction** — specify state, environment, coupling, boundaries, constraints, uncertainty, viability, and available control authority.
3. **Calculate** — solve or numerically propagate the actual governing equations. Undefined solution operators do not count as execution.
4. **Challenge** — independently test residuals, conservation, convergence, solver agreement, observations, domain validity, robustness, and recovery.

Layer 4 is not allowed to assume Layer 3 is correct.

## Operational modes

The safety layer uses five modes: NORMAL, RESTRICTED, SAFE, EMERGENCY, ISOLATE.

Loss of credibility must reduce permitted control authority. It must never only change a confidence number while leaving full actuator authority in place.

Default authority scaling implemented in safety.py:

| Mode | authority scale |
| --- | ---: |
| NORMAL | 1.00 |
| RESTRICTED | 0.50 |
| SAFE | 0.25 |
| EMERGENCY | 0.10 |
| ISOLATE | 0.00 |

Threshold values are provisional until calibrated against verified solver error distributions. They are not physical constants.

## Risk vector

Do not compress risk to one average before inspection. Track physics/model residual risk, numerical risk, state/measurement uncertainty, control-authority risk, external/environmental risk, and model-mismatch risk.

The operational mode uses the maximum component so one severe failure cannot be hidden by several low-risk components.

## Boundary/environment cases

Every stress run must explicitly identify one of:

1. closed_strong — the modelled environmental transfer channel is closed and containment capacity is tested against internal load;
2. weak_containment — the boundary can transmit environmental influence and can itself fail when load reaches capacity;
3. open — the environment participates continuously through coupling/flux.

Containment does not imply internal safety. A closed system can still develop large pressure, temperature, stress, vorticity, or other internal loads.

## Overpowering-event diagnostics

Track at minimum effective disturbance/restoring dominance, duration above restoring capacity, response-timescale/disturbance-timescale ratio, concentration factor, geometric amplification, coupling effectiveness, cascade gain, and distance to the recoverability boundary.

These are domain-supplied diagnostics, not universal physical constants.

## Robustness and recovery

For a fixed predicted outcome, search for the smallest admissible perturbation that changes the outcome. Separately search for the least intervention cost that returns a disturbed state to the viable/recoverable region.

Report both. A state can be robust but unrecoverable after boundary crossing, or fragile but easy to recover.

## Human-error controls

High-consequence runs should include explicit units and dimensional checks; scalar input provenance and uncertainty; immutable/fingerprinted configurations; reproducible solver/grid/timestep/random-seed manifests; invalid configuration blocking rather than silent coercion; predeclared acceptance criteria; preservation of previous known-good versions; independent/simple watchdog checks; and no single input, sensor, model, solver, or human action as the sole authority for an irreversible high-consequence action.

## Model mismatch

Unknown unknowns cannot be predicted individually. The required countermeasure is to detect disagreement between model and observation or departure from the validated domain.

A model-mismatch flag must mark the prediction untrusted, move operation to at least SAFE, reduce authority, preserve evidence for diagnosis, and require revalidation before returning to normal authority.

## Singularity claims

No single large numerical value is sufficient to declare a Navier–Stokes singularity. A candidate must survive systematic spatial refinement, timestep refinement, PDE residual convergence, incompressibility residual convergence, energy-accounting checks, estimated singular-time convergence, and an independent solver or numerical method.

Until those gates pass, use candidate singularity, not singularity proven.

## Required adversarial injections

Stress testing should intentionally include wrong viscosity or other physical parameter, corrupted state samples, wrong boundary condition, delayed forcing, excessive timestep, coarse resolution, sign-reversed control, actuator saturation, missing forcing component, rapidly changing environment, sensor drift, hidden-state perturbation, large cancelling PDE terms, model-domain violation, common-mode solver assumptions, and configuration/unit mistakes.

A test passes when the system either returns the independently verified result or correctly refuses to trust the result and reduces authority.

## Claims boundary

This safety shell can increase the credibility and failure tolerance of a simulation. It does not turn numerical evidence into a Navier–Stokes proof and does not guarantee that all unknown physical mechanisms have been represented.
