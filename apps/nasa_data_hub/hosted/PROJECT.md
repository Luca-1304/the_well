# NASA Data Hub — Public Maintainer Contract

This document defines the public technical boundary for maintaining and releasing NASA Data Hub. Product planning, private deployment administration, credentials, account access and internal priorities are deliberately managed outside this public repository.

## Scope

NASA Data Hub presents selected public NASA and EONET data through a readable, source-linked interface. The hosted application currently supports:

- Astronomy Picture of the Day
- Near-Earth Objects
- DONKI space weather
- EONET natural events

Production: https://nasa-data-hub.vercel.app

## Repository responsibility

This repository contains only the public-safe material required to understand, test and reproduce the application:

- Browser interface and feature modules
- Serverless request adapter
- Route validation and security-header configuration
- Automated tests and production smoke checks
- Public contributor and release instructions

It must not contain:

- API keys or deployment tokens
- Account, billing or firewall administration
- Private operational backlogs or personal planning
- Unredacted response data containing credentials
- Internal access instructions

## Security boundary

1. The browser never receives a NASA API key.
2. The serverless adapter injects a key only into requests to supported NASA endpoints.
3. Any echoed `api_key` query parameter is recursively removed before data is cached or returned.
4. EONET requests never receive the NASA key.
5. Shared links are rebuilt from an allow-list of public filters.
6. External links accept only HTTP or HTTPS and use `noopener noreferrer`.
7. The application is a restricted adapter, not an open proxy.
8. No user account, advertising tracker or third-party analytics profile is created.

## Source validation

Node.js 22 is required.

From this directory:

```bash
npm run check
```

This command performs syntax, unit, security and regression checks against proposed source. Production parity is intentionally not a pre-merge requirement when a change modifies deployable assets.

## Release verification

After a verified change is merged and deployed:

```bash
npm run release:check
```

This runs source checks and quota-free structural verification against production, including static-asset parity.

For releases that change API behaviour, or for a bounded live investigation:

```bash
npm run release:check:full
```

Full verification calls the supported public data routes and consumes a small amount of NASA quota. It must not be used as continuous polling.

## Release contract

A release is complete only when all applicable evidence exists:

### Source and CI

- JavaScript syntax checks pass
- Hosted unit and security tests pass on Node 22
- NASA package checks pass
- Repository formatting and tests pass
- No real environment file is tracked

### Production

- Deployment reaches `READY`
- The canonical alias points to the intended deployment
- `/api/health` reports the expected version and runtime
- Security headers remain present
- Deployed static assets match canonical source
- Invalid requests fail closed and are not cached
- Returned data contains no credential-shaped values
- Runtime logs contain no unexplained warning, error or fatal event

### Rendered changes

Visual or interaction changes also require desktop, narrow-screen and keyboard inspection. Automated source tests do not substitute for rendered evidence.

## Deployment boundary

GitHub source is public. Deployment settings, environment variables, firewall controls, billing and rollback permissions belong to the private hosting control plane.

Until the application is migrated to a dedicated repository, this directory remains the canonical public source. A future migration must preserve commit attribution where practical, prove the new deployment path before removing this source, and keep the last known-good production deployment available for rollback.

## Accuracy

NASA Data Hub is an independent project and is not an official NASA service. Source data may be delayed, revised or incomplete. The interface does not predict impacts and must not replace scientific, operational or local emergency guidance.
