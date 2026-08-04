# NASA Data Hub

A readable, source-linked dashboard for selected public NASA and EONET data.

**Production:** https://nasa-data-hub.vercel.app

NASA Data Hub presents:

- Astronomy Picture of the Day media, explanation and attribution
- Near-Earth Object close approaches with size, speed and miss-distance context
- DONKI space-weather records as a dated timeline
- EONET natural events with categories, coordinates and reporting-source links

This is an independent project. It is not an official NASA service, does not predict impacts and must not replace scientific, operational or emergency guidance.

## Trust model

- No user accounts
- No advertising or third-party analytics
- NASA credentials remain server-side
- Returned payloads are recursively scrubbed for echoed `api_key` query parameters
- Shared URLs contain only allow-listed public filters
- External links accept HTTP(S) only and use `noopener noreferrer`
- Upstream text is rendered through safe DOM text APIs rather than `innerHTML`
- Strict CSP, clickjacking, MIME-sniffing, referrer and browser-permission protections
- Node.js 22 LTS in CI and production

The anonymous in-memory courtesy limiter reduces accidental quota concentration per warm function instance. It is not represented as a distributed firewall; coordinated abuse belongs at the Vercel platform layer.

## Repository layout

```text
api/nasa.js                  Serverless allow-listed proxy
features/                    Browser presentation modules
scripts/production-smoke.mjs Quota-safe and bounded live verification
styles.css                   Main interface styling
stability.css                Stability-specific visual fixes
tests/                       Node regression and security tests
vercel.json                  Routes and security headers
```

`MAINTAINERS.md` contains the public release and maintenance contract. Private backlog, account access, billing, secrets and deployment administration do not belong in this repository.

## Verify locally

Node.js 22 is required. No dependency installation is currently needed.

```bash
npm run check
```

After a merged release has been deployed:

```bash
npm run release:check
```

For a bounded live check of APOD, NeoWs, DONKI and EONET:

```bash
npm run release:check:full
```

Full mode consumes a small amount of NASA public quota and is intended for release verification or investigation, not frequent polling.

## Continuous verification

The standalone CI workflow runs the complete source, security and regression suite on Linux and Windows using Node.js 22.

The production-smoke workflow runs every six hours in structural mode. It checks the public alias, health contract, runtime identity, security headers and exact static-asset parity without calling quota-bearing NASA routes. A manual full mode performs one bounded live check of all four supported data families.

## Deploy to Vercel

Use the repository root as the Vercel project root. No build command is required.

Target Git integration:

```text
Repository: Luca-1304/nasa-data-hub
Production branch: main
Root directory: repository root
Preview deployments: pull requests
Production deployments: merged main only
```

Keep credentials in Vercel encrypted environment variables only. Never place a NASA key, Vercel token or account credential in source, commits, issues, pull requests, workflow inputs, browser code or chat.

Preserve the previous READY production deployment until the new release has passed parity and live verification.

## Licence and origin

BSD 3-Clause. See [`LICENSE`](./LICENSE) and [`ORIGIN.md`](./ORIGIN.md).
