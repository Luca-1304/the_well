# NASA Data Hub — Project Operating Record

This file is the single operational source of truth for the hosted NASA Data Hub. GitHub Issues are disabled in this repository, so the ordered backlog, release rules, current state and next action live here rather than being scattered across chats, pull requests and deployment comments.

## Current state

| Field | Value |
|---|---|
| Product state | Active production service |
| Current release | 1.2.0 |
| Production | https://nasa-data-hub.vercel.app |
| Runtime | Node.js 22.x |
| Canonical source | `master/apps/nasa_data_hub/hosted` |
| Vercel project | `nasa-data-hub` |
| Last verified production deployment | `dpl_FHf2T2igNv3G3adgrucA2DFe29wr` |
| Last verified date | 2026-08-03 |
| Current API-key mode | NASA public `DEMO_KEY` |
| Account model | No user accounts |
| Tracking model | No advertising or third-party analytics |

## Purpose

Present selected public NASA and EONET data through a readable, source-linked and privacy-conscious interface without exposing credentials or overstating scientific certainty.

The product currently covers:

- Astronomy Picture of the Day
- Near-Earth Objects
- DONKI space weather
- EONET natural events

## Non-negotiable rules

1. **GitHub `master` is canonical.** Production must match the merged source exactly.
2. **Secrets remain private infrastructure.** Never place a NASA key, Vercel token or account credential in source, issues, pull requests, workflow inputs, browser code or chat.
3. **Public source, private control plane.** Interface code and serverless adapter code may be public; deployment permissions, billing, secrets and account access remain private.
4. **Evidence before completion.** Code existence is not completion. Use automated tests, live response checks or retained visual evidence as appropriate.
5. **No capability inflation.** Do not describe the in-memory courtesy limiter as a distributed firewall, the dashboard as an official NASA service, or event presence as an impact prediction.
6. **Keep the product lean.** Add a feature only when it improves comprehension, trust, reliability or meaningful utility.
7. **Rollback must remain possible.** Never destroy the last known-good production deployment during a release.

## System boundary

### Public

- Static browser interface
- Serverless adapter source
- Tests and monitoring source
- Security-header configuration
- Public NASA and EONET responses after credential redaction
- Shared URLs containing allow-listed public filters

### Private

- `NASA_API_KEY`
- Vercel and GitHub account permissions
- Deployment credentials
- Billing and firewall configuration
- Any future operational secrets

## Normal change flow

Use this path for every meaningful change:

1. Create a focused branch from current `master`.
2. State the behavioural contract before implementation when the change is non-trivial.
3. Make the smallest complete change.
4. Run `npm run check` against the proposed source.
5. Open a pull request containing the purpose, risk and evidence.
6. Require the hosted Node gate, NASA package checks and repository tests to pass.
7. Merge only the verified head SHA.
8. Deploy from merged `master`, never from an unmerged local variant.
9. Run `npm run release:check` against the deployed release to prove production parity.
10. Run `npm run release:check:full` when the release changes API behaviour or when investigating a live failure.
11. Record the production deployment ID and any known verification boundary.
12. Preserve the previous READY deployment for rollback.

Production parity belongs after deployment. A pull request that intentionally changes static assets should not be expected to match the previous production release before it is merged and deployed.

## Standard commands

From `apps/nasa_data_hub/hosted`:

```bash
# Proposed-source syntax, unit, security and regression checks.
npm run check

# Post-deployment source checks plus quota-free production parity.
npm run release:check

# The same post-deployment checks followed by one bounded live check of all data families.
npm run release:check:full
```

The full command consumes a small amount of NASA public quota. Use it for release verification or investigation, not continuous polling.

## Release acceptance

A release is acceptable only when all applicable checks are satisfied:

### Source and CI

- [ ] JavaScript syntax checks pass
- [ ] Hosted unit and security tests pass on Node 22
- [ ] NASA package tests pass
- [ ] Repository pre-commit passes
- [ ] Full repository tests pass on supported Python versions
- [ ] No real environment file is tracked

### Production

- [ ] Deployment reaches `READY`
- [ ] Canonical alias points to the intended deployment
- [ ] `/api/health` reports the expected app version and Node runtime
- [ ] `X-App-Version` matches the release
- [ ] Security headers remain present
- [ ] Static assets match canonical GitHub source
- [ ] Invalid requests fail closed and are not cached
- [ ] API responses contain no credential-shaped values
- [ ] Runtime logs contain no unexplained warning, error or fatal event

### Visual changes

- [ ] Desktop layout inspected
- [ ] Narrow mobile layout inspected
- [ ] Keyboard navigation inspected
- [ ] Loading, empty and error states inspected
- [ ] Relevant screenshots retained as evidence

Automated source tests do not substitute for rendered visual verification.

## Ordered backlog

Work from the top. Do not start a lower section merely because it is more interesting.

### Now — remove manual operational risk

1. **Complete browser-based desktop and mobile QA.**
   - keyboard-only navigation
   - narrow, tablet and desktop widths
   - loading, empty and error states
   - APOD image and video presentation
   - retained screenshots

2. **Connect Vercel directly to the repository.**
   - repository: `Luca-1304/the_well`
   - production branch: `master`
   - root directory: `apps/nasa_data_hub/hosted`
   - preview deployment for pull requests
   - production deployment only from merged `master`

3. **Prove the first Git-triggered deployment.**
   - confirm version and Node runtime
   - run structural source-parity smoke
   - run one bounded full smoke
   - document rollback to the previous READY deployment

4. **Configure Vercel firewall or bot controls.**
   - protect against distributed abuse at the platform layer
   - retain the app courtesy limiter as a secondary lightweight control

### Next — improve public credibility

1. Add and verify a dedicated Open Graph/social preview image.
2. Add NASA Data Hub to Luca's portfolio as an accurate technical case study.
3. Review accessibility with rendered browser tooling.
4. Review production performance using rendered measurements rather than source estimates.
5. Decide whether a custom domain materially improves trust before spending money.

### Later — only when evidence justifies it

1. Add a newly rotated private NASA key only if `DEMO_KEY` quota becomes a measured constraint.
2. Add privacy-preserving operational metrics only when they answer a defined product question.
3. Add another data family only when it improves the product rather than inflating feature count.

## Known verification boundary

The connected browser was unavailable during the 1.2 release. The release has source tests, cross-platform reliability evidence, exact uploaded-package verification, runtime identity checks, live API checks, security-header checks and clean runtime logs, but it does not claim screenshot-based desktop or mobile sign-off.

## Next concrete action

Enable or reconnect the browser integration, then complete the visual QA item at the top of the backlog. After that, connect Vercel Git integration so deployment no longer requires manual file upload.
