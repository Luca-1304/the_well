# NASA Data Hub v1.1 Design

## Purpose

Turn the existing secure NASA Data Hub prototype into a credible, understandable public product without adding accounts, tracking, unnecessary infrastructure or hidden claims.

## Product boundary

- The website and public-safe implementation remain public.
- NASA credentials, Vercel access, deployment permissions, billing and operational controls remain private.
- Shared URLs may contain only public filters such as dates, event type, status and category.
- The site stores no personal profile and adds no analytics or advertising trackers.
- The product must state clearly that it is independently built and is not an official NASA service.

## User experience

The dashboard keeps four focused data families: APOD, Near-Earth Objects, DONKI space weather and EONET natural events.

Results become human-readable views rather than raw JSON:

- APOD: media, title, date, explanation, attribution and official source link.
- Near-Earth Objects: sortable table with diameter range, speed, miss distance, lunar distance, approach time and hazard status.
- DONKI: chronological timeline with expanded event names and compact source-backed metadata.
- EONET: event cards with category, location/coordinates, observation time and source links.

Each section retains an optional raw-data disclosure for technical inspection.

## Trust and sharing

A visible trust footer includes NASA/EONET attribution, source-code link, last successful refresh time, privacy statement and availability/accuracy disclaimer. Share controls use the browser URL and clipboard only. They never include credentials, response payloads, browser identity or account information.

## Architecture

The frontend remains dependency-free browser modules rather than moving to React. `index.html` contains semantic structure; `styles.css` owns the visual system; `app.js` handles health, navigation and shared state; feature modules own rendering and query handling; `common.js` owns safe DOM, fetch and formatting helpers.

The serverless adapter remains a strict allow-listed proxy. It gains instance-local in-flight request deduplication and a best-effort anonymous courtesy limiter. The limiter is explicitly documented as quota protection, not a complete security perimeter; Vercel firewall controls remain the correct layer for distributed abuse.

## Reliability and security

- Credentials remain server-side and are recursively removed from upstream payload links before responses are returned.
- No `innerHTML` is used for upstream content.
- External links are restricted to HTTP(S), open in a new tab and use `noopener noreferrer`.
- Health/errors use `Cache-Control: no-store`; successful public data remains CDN-cacheable.
- Invalid requests fail before network access.
- Automated tests cover successful mocked routes, malformed JSON, retries, timeouts, rate limiting, deduplication, secret redaction, frontend secret isolation and share-state allow-listing.

## Deliberate non-goals

No accounts, database, subscriptions, AI summaries, private key deployment, broad endpoint expansion, third-party analytics or custom domain are included in v1.1.
