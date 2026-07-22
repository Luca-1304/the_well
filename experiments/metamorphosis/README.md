# Navier–Stokes Metamorphosis Research Track

## Purpose

This directory isolates a falsifiable research programme built around the 3D incompressible Navier–Stokes existence-and-smoothness problem, while allowing controlled-flow, thermal, optical, magnetic, preservation, and machine-learning extensions to be tested without confusing them with a formal proof.

The primary mathematical target is:

\[
\sup_{t\ge 0}\|\nabla u(t)\|_\infty < \infty.
\]

The practical control question is:

> What rule makes redistribution increase automatically whenever concentration increases?

## Core equations

Incompressible Navier–Stokes:

\[
\partial_t u + (u\cdot\nabla)u = -\frac{1}{\rho}\nabla p + \nu\Delta u + f_{\mathrm{ctrl}},
\qquad \nabla\cdot u = 0.
\]

Vorticity:

\[
\omega = \nabla\times u,
\qquad \Omega(t)=\|\omega(t)\|_\infty.
\]

Temperature transport:

\[
\rho c_p(\partial_t T + u\cdot\nabla T)=k\Delta T+Q.
\]

Thermal boundary condition:

\[
-k\nabla T\cdot n = h(T-T_{\mathrm{ext}}).
\]

## Working continuation hypothesis

Rising concentration must trigger a redistribution response that grows at least as quickly:

\[
\Omega(t)\uparrow \Longrightarrow
\mathcal D_\nu(t)+\mathcal S(t)+\mathcal C(t)\uparrow.
\]

The initial diagnostic ratio is:

\[
\mathcal R_M(t)=
\frac{\mathcal V_\omega(t)}
{\mathcal D_\nu(t)+\mathcal S(t)+\mathcal C_B(t)+\mathcal C_p(t)+\mathcal C_T(t)+\mathcal C_{\partial\Omega}(t)}.
\]

This ratio is a research diagnostic, not an established theorem. The desired controlled condition is \(\mathcal R_M(t)\le 1\).

## Preservation target

Let \(X\) denote whatever essential matter, structure, organisation, information, or function must survive for the test object to continue existing for its intended purpose.

\[
P_{\mathrm{exist}}=
\min(P_{M_e},P_{C_e},P_{S_e},P_{I_e},P_{F_e}).
\]

A controlled test succeeds only if:

1. velocity gradients and vorticity remain finite over the test interval;
2. flow continues after peak concentration;
3. the essential preservation score exceeds its purpose-specific threshold;
4. the result is reproduced by an independent solver or dataset comparison.

## Research lanes

### Lane A — Pure Navier–Stokes

No added controller. Study whether viscosity and the equation's own geometry control vortex stretching for permitted smooth initial data. Weak solutions, energy inequalities, continuation criteria, and known regularity results belong here.

### Lane B — Controlled-space continuation

Add boundary, pressure, thermal, magnetic, or geometric controls and test whether concentration can be regulated into continued flow. Success here is engineering evidence, not automatically a solution to the unrestricted Clay problem.

### Lane C — Metamorphosis extensions

Track preservation of \(X\), temperature-dependent material properties, optical phase-conjugate observation, MHD control, and adaptive switching between control mechanisms.

## First experiment ladder

1. Baseline fluid trajectory with no control.
2. Compute \(\|\nabla u\|_\infty\), \(\|\omega\|_\infty\), energy, and dissipation.
3. Track a marked passive scalar as the first preservation object \(X\).
4. Add exterior-temperature coupling and temperature-dependent viscosity.
5. Add adaptive boundary feedback.
6. Compare conventional numerical results with a PINN.
7. Add magnetic, pressure, optical, or multi-field controls one at a time.

## Guardrails

- Do not call numerical smoothness a proof of global regularity.
- Keep symbolic concepts separate from established operators and theorems.
- Check dimensions and units for every derived quantity.
- Compare PINNs against conventional solvers; do not rely on one model.
- Use `viscoelastic_instability_v2`, not the deprecated dataset.
- Treat every failure as information about the next valid question.
