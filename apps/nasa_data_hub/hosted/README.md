# NASA Data Hub — Hosted Edition

This folder is the public-safe, reproducible source for the hosted NASA Data Hub:

**Production:** https://nasa-data-hub.vercel.app

The website is intentionally public because it presents public NASA and EONET data. Credentials, deployment permissions, account access, billing and operational controls remain private.

## Product views

Version 1.2 presents the four supported data families as readable interfaces rather than raw API output:

- Astronomy Picture of the Day with uncropped media, explanation, attribution and official publication links.
- Near-Earth Objects in a sortable table with diameter, speed, miss distance, lunar-distance equivalents and hazard classification context.
- DONKI space-weather records as a chronological timeline with expanded event names and source links.
- EONET natural events as source-backed cards with category, latest geometry and reporting-agency links.

Every view retains an optional raw public response disclosure for technical inspection.

Version 1.2 also improves interaction reliability:

- Date defaults follow the visitor's local calendar rather than UTC serialisation.
- APOD and observational space-weather inputs cannot select future dates.
- Near-Earth Object queries may use valid future dates but remain constrained to NASA's seven-day feed window.
- A newer request aborts an older request for the same view, preventing stale results from replacing current results.
- Non-JSON gateway failures become controlled public messages rather than broken rendering.
- Result regions expose an accessible busy state while loading.
- The serverless runtime is pinned to Node.js 22 LTS and identified by the health endpoint.

## Trust boundary

### Public

- Browser interface and source
- Serverless adapter source
- Routing and security-header configuration
- Tests and deployment documentation
- Public NASA and EONET response data after credential redaction
- Shared URLs containing only allow-listed public filters

### Private

- `NASA_API_KEY`
- Vercel account and project settings
- GitHub/Vercel deployment permissions
- Billing, firewall and monitoring controls

The browser never receives the API key. The serverless function adds it only to requests sent to `api.nasa.gov`, then recursively removes any `api_key` query parameter NASA may echo inside response links before the response is cached or returned. EONET requests never receive the NASA key.

The site creates no account or advertising profile and includes no third-party analytics or advertising scripts.

## Secure sharing

Each view can produce a shareable URL. The URL is rebuilt from an allow-list and may contain only the relevant public date, event type, status, category and sort filters. Existing query strings, tracking parameters, unknown fields and credential-shaped values are discarded.

Sharing uses the browser clipboard when available. No response payload, account identifier or credential is embedded in the URL.

## Quota protection

The proxy applies two lightweight protections:

1. Identical simultaneous upstream requests share one in-flight operation per warm serverless instance.
2. A temporary, anonymous courtesy limit reduces the chance that one browser consumes the shared public quota.

The courtesy limiter stores only an ephemeral request count associated with the platform-provided client address inside a warm function instance. It is not a durable user profile and is not claimed as a distributed security firewall. Vercel firewall and bot controls remain the appropriate layer for coordinated or distributed abuse.

The production deployment deliberately uses NASA's public `DEMO_KEY` until higher limits are actually necessary. Never paste a newly rotated private key into source, commits, issues, pull requests, workflow inputs, browser code or chat.

## Run the checks

Node.js 22 is required and matches the production runtime.

```bash
npm run check
```

The checks cover:

- JavaScript syntax
- Successful mocked upstream routes
- Retry and malformed-response handling
- Recursive key redaction, including mixed-case query parameters
- Correct EONET `/api/v3/events` routing
- Versioned health responses and runtime identity
- Rejection of invalid NEO and EONET windows
- In-flight request deduplication
- Superseded browser-request cancellation
- Anonymous courtesy limits
- Frontend credential isolation and absence of unsafe HTML sinks
- Secure share-state allow-listing
- Local-calendar date handling and NEO window calculations
- Visible attribution, privacy and independence statements
- Production smoke assertion and exact asset-parity behaviour

## Production monitoring

The repository includes a dedicated `NASA Data Hub Production Smoke` workflow.

Scheduled runs execute every six hours in **structural** mode. They verify the public alias, v1.2 health contract, Node 22 runtime identity, hardened security headers and exact equality between production static files and the canonical files in GitHub. These checks do not call quota-bearing NASA data routes.

A manual workflow run can select **full** mode. Full mode performs one bounded check against APOD, NeoWs, DONKI and EONET, verifies that returned payloads remain credential-free, and confirms that an invalid NeoWs window fails with an uncached HTTP 400 response.

The same checks can be run locally:

```bash
npm run smoke:production
npm run smoke:production:full
```

Full mode intentionally consumes a small amount of the public NASA quota and should be used for release verification or investigation, not frequent polling.

## Deploy to Vercel

Set this folder as the project root:

```text
apps/nasa_data_hub/hosted
```

No build command is required. `package.json` pins Node.js 22.x so Vercel and CI use the same major runtime.

For higher limits, create a newly rotated NASA key and add it directly through:

```text
Vercel Project → Settings → Environment Variables
Name: NASA_API_KEY
Targets: Production and Preview as needed
```

Redeploy after adding or changing an environment variable so the new function receives it.

## Security controls

- Strict route allow-list; this is not an open proxy.
- Server-side credential injection only.
- Recursive credential removal from nested upstream payloads.
- Same-origin browser requests.
- Safe DOM rendering; no upstream content is inserted through `innerHTML`.
- HTTP(S)-only external-source links using `noopener noreferrer`.
- Request validation for dates, limits, event types and category length.
- Fifteen-second upstream timeout and bounded retries.
- Public-data CDN caching plus in-flight deduplication.
- API errors and health responses use `Cache-Control: no-store`.
- CSP without inline-script permission, clickjacking protection, MIME sniffing protection, restrictive permissions policy and no-referrer policy.
- No application logging of request URLs or credential values.
- Version and runtime metadata contain no credential or account information.

## Accuracy and attribution

This is an independent project and is not an official NASA service. NASA and EONET data remain subject to their source terms, timing, corrections and attribution requirements. The interface does not predict impacts and must not replace scientific, operational or local emergency guidance.

The repository's origin and upstream authorship are documented in the root `ORIGIN.md`.
