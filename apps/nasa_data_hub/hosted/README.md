# NASA Data Hub — Hosted Edition

This folder is the public-safe, reproducible source for the hosted NASA Data Hub:

**Production:** https://nasa-data-hub.vercel.app

The website is intentionally public because it displays public NASA and EONET data. Credentials and deployment controls remain private.

## Trust boundary

### Public

- `index.html`
- Serverless API source
- Routing and security-header configuration
- Tests and deployment documentation
- Public NASA and EONET response data after credential redaction

### Private

- `NASA_API_KEY`
- Vercel account, project settings and deployment permissions
- Any future monitoring, billing or custom-domain controls

The browser never receives the API key. The serverless function adds it only to requests sent to `api.nasa.gov`, then recursively removes any `api_key` query parameter that NASA may echo inside response links before the response is cached or returned.

EONET requests never receive the NASA key.

## Run the checks

Node.js 20 or newer is required.

```bash
npm run check
```

The checks cover:

- JavaScript syntax
- Recursive key redaction, including mixed-case query parameters
- Correct EONET `/api/v3/events` routing
- Health responses without network access
- Rejection of invalid NEO windows
- Confirmation that frontend source contains no secret-access code

## Deploy to Vercel

Set this folder as the project root:

```text
apps/nasa_data_hub/hosted
```

No build command is required.

The application works without a personal credential by using NASA's public `DEMO_KEY`. For higher limits, create a newly rotated key and add it through:

```text
Vercel Project → Settings → Environment Variables
Name: NASA_API_KEY
Targets: Production and Preview as needed
```

Do not paste the key into source, commits, pull requests, issues, workflow inputs or frontend JavaScript.

After adding or changing an environment variable, redeploy so the new serverless functions receive it.

## Security controls

- Strict route allow-list; this is not an open proxy.
- Server-side credential injection only.
- Recursive credential removal from nested upstream payloads.
- Request validation for dates, limits, event types and category length.
- Fifteen-second upstream timeout and bounded retries.
- Public-data CDN caching to reduce upstream quota pressure.
- API errors and health responses use `Cache-Control: no-store`.
- CSP, clickjacking protection, MIME sniffing protection, restrictive permissions policy and no-referrer policy.
- No server-side logging of request URLs or credential values.

## Relationship to the Python edition

The parent folder contains the full Python package, local dashboard, CLI, caching, diagnostics and cross-platform reliability suite. This hosted edition is deliberately thin: it preserves the same four data families while matching Vercel's serverless runtime.

## Licensing and attribution

NASA and EONET data remain subject to their respective source terms and attribution requirements. This hosted adapter is maintained as a Luca-specific addition inside the public `Luca-1304/the_well` repository; the repository's origin and upstream authorship are documented in the root `ORIGIN.md`.
