# Navier–Stokes Metamorphosis Research Track

## Purpose

This directory isolates a falsifiable research programme built around the 3D incompressible Navier–Stokes existence-and-smoothness problem, while allowing controlled-flow, thermal, optical, magnetic, preservation, and machine-learning extensions to be tested without confusing them with a formal proof.

The executable Python implementation is installed under `the_well.research.metamorphosis`; this directory retains the research specification, configuration and verification contract.

The primary finite-time continuation target is:

\[
\sup_{0\le t\le T}\|\nabla u(t)\|_\infty < \infty
\qquad \text{for every finite }T.
\]

This is intentionally different from demanding one uniform bound for all infinite future time.

The practical control question is:

> What physically defined rule makes redistribution increase automatically whenever concentration increases?

## Claim hierarchy

1. **Established mathematics:** governing equations, weak solutions, energy inequalities, known continuation criteria, and verified numerical methods.
2. **Research hypotheses:** concentration-versus-redistribution diagnostics and candidate control laws.
3. **Engineering evidence:** reproducible controlled simulations or experiments.
4. **Speculative extensions:** Metamorphosis, optical phase conjugation, MHD, adaptive multi-field switching, and preservation of a general object `X`.

No result from levels 2–4 is to be described as a Navier–Stokes proof unless it supplies a rigorous argument for all permitted 3D initial data.

## Core equations

Incompressible Navier–Stokes:

\[
\partial_t u + (u\cdot\nabla)u
= -\frac{1}{\rho}\nabla p + \nu\Delta u + f_{\mathrm{ctrl}},
\qquad \nabla\cdot u = 0.
\]

Vorticity and the 3D vorticity equation:

\[
\omega = \nabla\times u,
\qquad
\partial_t\omega + (u\cdot\nabla)\omega
= (\omega\cdot\nabla)u + \nu\Delta\omega + \nabla\times f_{\mathrm{ctrl}}.
\]

Temperature transport:

\[
\rho c_p(\partial_t T + u\cdot\nabla T)=k\Delta T+Q.
\]

Thermal boundary condition:

\[
-k\nabla T\cdot n = h(T-T_{\mathrm{ext}}).
\]

Passive marked-substance transport:

\[
\partial_t c + u\cdot\nabla c = \kappa_c\Delta c + q_c.
\]

The passive scalar `c` is the first computational representation of the substance or essential matter `X`.

## Working continuation hypothesis

The project tests whether a physically derived redistribution mechanism can grow strongly enough relative to the 3D vortex-stretching mechanism:

\[
\mathcal V_\omega = (\omega\cdot\nabla)u,
\qquad
\mathcal D_\omega = \nu\Delta\omega.
\]

The first dimensionless diagnostic is a norm ratio:

\[
\mathcal R_\omega(t)
=
\frac{\|\mathcal V_\omega(t)\|}
{\|\mathcal D_\omega(t)\|+\varepsilon}.
\]

Both terms have the same physical dimensions. This remains a diagnostic, not a theorem: norms can hide direction, cancellation, geometry, and local sign. In 2D, vortex stretching is identically zero, so a 2D run only validates infrastructure.

The desired controlled principle remains:

\[
\text{concentration rises}
\Longrightarrow
\text{a verified redistribution response rises without merely killing the flow}.
\]

## Preservation target

Let `X` denote whatever essential matter, composition, structure, organisation, information, or function must survive for the test object to continue existing for its intended purpose.

\[
P_{\mathrm{exist}}
=
\min(P_{M_e},P_{C_e},P_{S_e},P_{I_e},P_{F_e}).
\]

For the first marked-scalar test, only measurable material proxies are used initially: integrated marked mass and aligned spatial structure. More advanced identity, information, and function metrics require a purpose-specific definition.

A controlled test succeeds only if:

1. velocity gradients and vorticity remain finite over the stated finite interval;
2. the flow remains meaningfully active after peak concentration;
3. the essential preservation score exceeds its purpose-specific threshold;
4. the result is reproduced by an independent solver, analytic solution, or dataset comparison;
5. reduced peaks are not explained solely by indiscriminate damping.

## Research lanes

### Lane A — Pure Navier–Stokes

No added controller. Study whether viscosity and the equation's own geometry control vortex stretching for permitted smooth initial data. Weak solutions, energy inequalities, continuation criteria, and known regularity results belong here.

### Lane B — Controlled-space continuation

Add boundary, pressure, thermal, magnetic, or geometric controls and test whether concentration can be regulated into continued flow. Success here is engineering evidence, not automatically a solution to the unrestricted Clay problem.

### Lane C — Metamorphosis extensions

Track preservation of `X`, temperature-dependent material properties, optical phase-conjugate observation, MHD control, and adaptive switching between control mechanisms.

## Current implementation

Implemented:

- automatic-differentiation residuals for incompressible Navier–Stokes;
- temperature and passive-scalar residuals;
- finite-difference velocity gradients, vorticity, kinetic energy, vortex stretching, and viscous diffusion;
- purpose-relative preservation classes and marked-scalar mass/overlap metrics;
- a bounded vorticity-weighted damping baseline;
- an analytic 2D Taylor–Green verification runner;
- a 3D periodic Fourier-pseudospectral Navier–Stokes solver with Leray projection, 2/3 de-aliasing, RK4 and step-doubling;
- passive-scalar transport in the 3D time loop;
- live 0→1→2→3→4 safety decisions inside each accepted 3D step;
- uncontrolled/controlled twin-run support from the same initial state;
- a distinct second-order finite-difference + RK2 projection solver for short-horizon cross-validation;
- analytic and adversarial tests for the PDE residuals, diagnostics, safety shell and 3D solver.

Not implemented yet:

- a The Well dataset adapter;
- literal-wall boundary mechanics and genuine pressure, thermal, or counter-vorticity redistribution controllers;
- a PINN model and The Well comparison;
- optical, MHD, and adaptive switching extensions.

## Experiment ladder

0. Verify differential operators against analytic solutions.
1. Run the 2D Taylor–Green baseline as an infrastructure test.
2. Track a marked passive scalar and define measurable preservation proxies.
3. Run the conventional 3D numerical solver and compare uncontrolled flow with the damping baseline.
4. Cross-check the 3D periodic vortex case against the independent finite-difference/RK2 path.
5. Derive and compare stretching and redistribution directly from the vorticity and enstrophy equations.
6. Add exterior-temperature coupling and temperature-dependent material properties.
7. Test boundary, pressure, counter-vorticity, and thermal controls separately.
8. Compare conventional numerical results, The Well data, and a PINN.
9. Add magnetic, optical, or multi-field controls one at a time.

## Running the analytic baseline

From the repository root after installing the package:

```bash
python -m the_well.research.metamorphosis.run_analytic_baseline
pytest tests/test_metamorphosis.py
```

The analytic baseline is not evidence about 3D global regularity. Its purpose is to catch incorrect derivatives, signs, norms, and numerical plumbing before a costly experiment.

## Guardrails

- Do not call numerical smoothness a proof of global regularity.
- Keep symbolic concepts separate from established operators and theorems.
- Check dimensions and units for every derived quantity.
- State the exact norm used for every boundedness claim.
- Distinguish damping from redistribution and continued flow.
- Compare PINNs against conventional solvers; do not rely on one model.
- Use `viscoelastic_instability_v2`, not the deprecated dataset.
- Treat every failure as information about the next valid question.
## Safety-hardening layer

The research track now uses a 0→1→2→3→4 architecture:

0. validate model/domain/inputs;
1. identify and normalise drivers;
2. specify interaction, boundary, environment, uncertainty, viability and control authority;
3. calculate the governing dynamics;
4. independently challenge the result and reduce authority on loss of credibility.

Executable safety utilities live in `the_well.research.metamorphosis.safety`.
The adversarial contract is `experiments/metamorphosis/SAFETY.md`, with the
machine-readable stress matrix in `configs/safety_stress.yaml`.

Safety additions include:

- explicit validity gates and parameter provenance;
- physics/numerical/uncertainty/control/external/mismatch risk separation;
- NORMAL → RESTRICTED → SAFE → EMERGENCY → ISOLATE authority modes;
- model-mismatch detection that automatically reduces control authority;
- closed, weak-containment and open boundary/environment scenarios;
- overpowering-event diagnostics for dominance, duration, response speed,
  concentration, geometry, coupling, cascades and recoverability;
- minimum tested distance-to-failure and recovery-cost metrics;
- deterministic configuration fingerprints for reproducibility;
- enstrophy, stretching-production and viscous-dissipation integral diagnostics.

The safety layer is a credibility and containment mechanism, not evidence of
global regularity and not a substitute for an independent solver.


## Running the 3D safety-integrated experiment

From the repository root:

```bash
python -m the_well.research.metamorphosis.run_3d_simulation
python -m the_well.research.metamorphosis.run_3d_verification
pytest tests/test_metamorphosis_solver3d.py
pytest tests/test_metamorphosis_cross_validation.py
```

The default 3D runner executes uncontrolled and controlled Taylor–Green lanes
from the same initial state and, unless explicitly skipped, also runs the
finite-difference/RK2 cross-validation path.

The periodic solver has no literal solid wall. Its closed/weak/open
containment modes are an explicit environment-coupling abstraction. Physical
wall deformation or fracture must be tested in a separate boundary-mechanics
solver before making claims about real containment failure.


### Live failure-tolerance behaviour

The 3D loop now also includes:

- configuration provenance and a deterministic run fingerprint;
- pre-step authority reduction for known uncertainty/model mismatch;
- projected-force energy accounting;
- environmental-power versus viscous/control-removal dominance;
- enstrophy-production versus viscous-enstrophy-dissipation dominance;
- accumulated excess environmental energy relative to initial kinetic energy;
- sensor-scale drift and sign-reversed-controller fault hooks;
- optional integer-step controller latency;
- a hard watchdog that can override soft risk scoring and force isolation;
- optional shadow simulation after isolation with experimental authority fixed at zero;
- executable amplitude-robustness and recovery-effort sweeps;
- executable grid and timestep convergence sweeps.

A shadow run after isolation is for research only: the subsequent states remain
labelled untrusted and cannot be promoted back to normal authority without a
new validation decision.
