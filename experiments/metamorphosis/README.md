# Navier–Stokes Metamorphosis Research Track

## Purpose

This directory isolates a falsifiable research programme built around the 3D incompressible Navier–Stokes existence-and-smoothness problem, while allowing controlled-flow, thermal, optical, magnetic, preservation, and machine-learning extensions to be tested without confusing them with a formal proof.

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
- analytic tests for the PDE residuals and diagnostic operators.

Not implemented yet:

- a conventional time-stepping Navier–Stokes solver for the controlled run;
- a The Well dataset adapter;
- genuine boundary, pressure, thermal, or counter-vorticity redistribution controllers;
- the first 3D vortex-stretching experiment;
- a PINN model and independent model comparison;
- optical, MHD, and adaptive switching extensions.

## Experiment ladder

0. Verify differential operators against analytic solutions.
1. Run the 2D Taylor–Green baseline as an infrastructure test.
2. Track a marked passive scalar and define measurable preservation proxies.
3. Add a conventional numerical solver and compare uncontrolled flow with the damping baseline.
4. Move immediately to a 3D periodic vortex case where vortex stretching is non-zero.
5. Derive and compare stretching and redistribution directly from the vorticity equation.
6. Add exterior-temperature coupling and temperature-dependent material properties.
7. Test boundary, pressure, counter-vorticity, and thermal controls separately.
8. Compare conventional numerical results, The Well data, and a PINN.
9. Add magnetic, optical, or multi-field controls one at a time.

## Running the analytic baseline

From the repository root:

```bash
python -m experiments.metamorphosis.run_analytic_baseline
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
