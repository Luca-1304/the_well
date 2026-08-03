# NASA Data Hub v1.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the hosted NASA Data Hub into a readable, credible and securely shareable public product while preserving the existing credential boundary.

**Architecture:** Keep the dependency-free Vercel application. Split frontend behavior into focused browser modules, retain the strict serverless allow-list, add best-effort quota protection and verify every public route plus browser interactions before production deployment.

**Tech Stack:** HTML5, CSS, native ES modules, Node.js 20+, Vercel Functions, Node test runner, GitHub Actions.

## Global Constraints

- No accounts, database, third-party analytics, advertising trackers or AI-generated interpretations.
- Shared URLs contain only public allow-listed filter values.
- No private NASA credential is added or requested in chat.
- Upstream content is rendered through safe DOM APIs, never `innerHTML`.
- Existing CSP, frame denial, no-referrer, permissions policy and MIME protections remain active.
- The current four data families remain the complete v1.1 scope.

---

### Task 1: Modular, credible frontend

**Files:**
- Modify: `apps/nasa_data_hub/hosted/index.html`
- Create: `apps/nasa_data_hub/hosted/styles.css`
- Create: `apps/nasa_data_hub/hosted/app.js`
- Create: `apps/nasa_data_hub/hosted/features/common.js`
- Create: `apps/nasa_data_hub/hosted/features/apod.js`
- Create: `apps/nasa_data_hub/hosted/features/neo.js`
- Create: `apps/nasa_data_hub/hosted/features/donki.js`
- Create: `apps/nasa_data_hub/hosted/features/eonet.js`
- Create: `apps/nasa_data_hub/hosted/favicon.svg`

**Interfaces:**
- `requestJson(path, output): Promise<object|null>` performs safe same-origin API requests.
- `setShareState(view, params): void` updates only allow-listed public query state.
- Each feature exports `initFeature(context): void`.

- [ ] Replace raw result-first markup with semantic APOD, table, timeline and event-card containers.
- [ ] Add accessible loading, empty, error and raw-data disclosure states.
- [ ] Add source attribution, privacy, independence and availability statements.
- [ ] Add copy-link controls that serialize only public filters.
- [ ] Add responsive, keyboard-visible and reduced-motion styling.
- [ ] Run frontend source checks.
- [ ] Commit the frontend slice.

### Task 2: Quota protection and robust proxy behavior

**Files:**
- Modify: `apps/nasa_data_hub/hosted/api/nasa.js`
- Modify: `apps/nasa_data_hub/hosted/vercel.json`

**Interfaces:**
- `checkCourtesyLimit(request, mode): {allowed:boolean, retryAfter:number}`.
- `deduplicatedFetch(key, operation): Promise<object>` shares identical in-flight upstream work per warm function instance.

- [ ] Add anonymous instance-local courtesy limits for authenticated NASA routes.
- [ ] Add in-flight deduplication keyed without credentials.
- [ ] Return clear `429` responses with `Retry-After` and no-store.
- [ ] Preserve strict route validation, redaction, retries and cache behavior.
- [ ] Update CSP for external official-source links without permitting external script or connect origins.
- [ ] Commit the server slice.

### Task 3: Regression and browser tests

**Files:**
- Modify: `apps/nasa_data_hub/hosted/tests/nasa.test.mjs`
- Create: `apps/nasa_data_hub/hosted/tests/frontend.test.mjs`
- Modify: `.github/workflows/nasa-data-hub-hosted.yml`

**Interfaces:**
- Tests import pure exported proxy helpers and inspect frontend module source.

- [ ] Add mocked success tests for APOD, NEO, DONKI and EONET.
- [ ] Add malformed JSON, retry, rate-limit and deduplication tests.
- [ ] Prove shared state excludes unknown keys and credential-shaped values.
- [ ] Prove frontend modules contain no secret access and no unsafe HTML sink.
- [ ] Run `npm run check` in CI and locally-equivalent GitHub Actions.
- [ ] Commit tests.

### Task 4: Documentation, review, deployment and production verification

**Files:**
- Modify: `apps/nasa_data_hub/hosted/README.md`
- Modify: `apps/nasa_data_hub/README.md`

- [ ] Document readable views, secure sharing and the courtesy limiter's limitations.
- [ ] Open a pull request with explicit security and credibility claims.
- [ ] Require all relevant CI gates to pass.
- [ ] Squash-merge only after verification.
- [ ] Deploy the exact merged package to Vercel production.
- [ ] Verify desktop and mobile browser structure, all four routes, redaction, headers, sharing and failure states.
- [ ] Record post-deployment evidence on the pull request.
