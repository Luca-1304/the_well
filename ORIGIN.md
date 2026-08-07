# Project origin

NASA Data Hub was developed as a Luca-specific addition under `apps/nasa_data_hub/hosted` in [`Luca-1304/the_well`](https://github.com/Luca-1304/the_well).

This standalone export preserves that application source, its public technical history, tests and BSD 3-Clause licence while separating it from the unrelated parent monorepo.

The parent repository began as a research/reference copy of [`PolymathicAI/the_well`](https://github.com/PolymathicAI/the_well). NASA Data Hub is not part of the upstream PolymathicAI project, and this repository does not claim upstream dataset or research authorship.

NASA, EONET, DONKI and related names and data remain the property of their respective source organisations. This is an independent project and is not an official NASA service or endorsement.

## Export lineage

The first verified standalone snapshot was produced on 4 August 2026 as commit `0af07e335f3e4c472d396d747e8acf0b6e83c76d` on `export/nasa-data-hub-standalone-20260804`.

The hardened 7 August 2026 export was derived from that snapshot without changing the deployable product. Before the automation refresh, critical standalone files were compared against canonical `the_well` `master` at `63433d0158aae0f523ac6b45331b16244ed73783` and matched by exact Git blob SHA, including `package.json`, `api/nasa.js`, `app.js`, `scripts/production-smoke.mjs` and `vercel.json`.

The 7 August hardening changes are limited to standalone repository automation, workflow-security regression coverage and this provenance record. They do not change NASA API behaviour, browser behaviour, Vercel routing or security headers, product version, runtime contract or production state.

A future dedicated repository should preserve this lineage and record the exact dedicated-repository commit used for each Vercel preview and production deployment. Static asset parity is useful release evidence, but it must not be represented as proof of deployment commit identity when hosting metadata does not provide that identity.
