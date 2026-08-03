# NASA Data Hub

A standalone NASA integration that does **not** depend on the rest of `the_well`.

**Public hosted dashboard:** https://nasa-data-hub.vercel.app

The product is intentionally public because it presents public NASA and EONET data. Credentials, account access, deployment permissions, billing and operational controls remain private. Reproducible hosted source and its complete trust contract are in [`hosted/`](hosted/).

It provides:

- A local Python dashboard and command-line interface
- A public hosted dashboard with no account or advertising trackers
- Server-side proxying so the browser never receives the NASA key
- Astronomy Picture of the Day
- Near-Earth-object approaches and asteroid lookup
- DONKI space-weather events
- EONET natural events
- Retry handling, caching, diagnostics and tests
- A working out-of-box mode using NASA's public `DEMO_KEY`

## Hosted v1.1

The hosted edition turns the four public data families into readable, source-linked views:

- APOD media, explanation and attribution
- A sortable Near-Earth Object table with size, speed, miss distance, lunar distance and hazard context
- A DONKI event timeline with expanded event names
- EONET event cards with categories, observations, coordinates and reporting-agency links

Share controls rebuild the URL using only allow-listed public filters. They discard existing tracking parameters, unknown fields and credential-shaped values. The hosted proxy also deduplicates identical in-flight requests and applies an ephemeral anonymous courtesy limit to protect the shared public quota. This limit is intentionally described as quota protection rather than a distributed firewall.

## Start it on Windows

Open PowerShell in this folder:

```powershell
Copy-Item .env.example .env
notepad .env
```

Paste a **newly rotated** NASA key after `NASA_API_KEY=`. The key previously pasted into chat should be treated as exposed.

Then run:

```powershell
.\start.ps1
```

The dashboard opens at:

```text
http://127.0.0.1:8765
```

## Start it on macOS or Linux

```bash
cp .env.example .env
chmod +x start.sh
./start.sh
```

## It works before you add a personal key

When `NASA_API_KEY` is blank, the hub uses NASA's public `DEMO_KEY`. This has lower limits, but installation and both dashboards can be tested without a private credential.

Check local configuration without making a network request:

```bash
python -m nasa_data_hub health
```

Test configuration with a real APOD request:

```bash
python -m nasa_data_hub doctor
```

## Commands

```bash
python -m nasa_data_hub serve --open
python -m nasa_data_hub apod
python -m nasa_data_hub apod --date 2026-08-02
python -m nasa_data_hub neo --start 2026-08-02 --end 2026-08-05
python -m nasa_data_hub neo-lookup 3542519
python -m nasa_data_hub neo-browse --page 0 --size 20
python -m nasa_data_hub donki FLR --start 2026-08-01 --end 2026-08-02
python -m nasa_data_hub eonet --status open --days 14 --category wildfires
```

## Folder map

```text
apps/nasa_data_hub/
├── nasa_data_hub/       Python package, server, CLI, client and configuration
│   └── static/          Local browser dashboard assets
├── hosted/              Public-safe Vercel product, modules, tests and deployment contract
├── tests/               Offline Python unit tests
├── .env.example         Safe local configuration template
├── start.ps1            Windows launcher
├── start.sh             macOS/Linux launcher
└── README.md            This guide
```

## Security

- Never commit `.env`.
- Never place a real key in HTML or frontend JavaScript.
- The local dashboard talks only to the local Python server.
- The hosted dashboard talks only to its same-origin serverless API.
- Servers add the API key only to `api.nasa.gov` requests.
- EONET requests never receive the key.
- NASA credentials echoed inside nested response links are removed before responses are cached or returned.
- Cache and deduplication keys are derived from URLs with credentials removed.
- Upstream public content is rendered with safe DOM APIs rather than `innerHTML`.
- External links are restricted to HTTP(S) and isolated with `noopener noreferrer`.
- Errors do not include request URLs or API keys.
- The hosted edition uses strict routing, validation, CSP, frame denial, a restrictive permissions policy and no-referrer protection.

## Tests

From this folder:

```bash
python -m unittest discover -s tests -v
```

For the hosted edition:

```bash
cd hosted
npm run check
```

The hosted checks cover syntax, mocked success/failure routes, retries, malformed responses, credential redaction, request deduplication, courtesy limits, secure sharing, frontend secret isolation and visible credibility statements.

## Reliability gates

The `NASA Data Hub 20-pass reliability` workflow separates two kinds of evidence:

1. **Deterministic application reliability** runs automatically on relevant pull requests and pushes to `master`. Linux and Windows each perform ten complete passes followed by ten confirmation passes, covering build, clean installation, tests, startup and local route probes.
2. **Registered-key live API reliability** is a separate manual workflow option. It performs ten complete NASA API-family passes followed by ten confirmation passes and fails closed unless the repository has a newly rotated `NASA_API_KEY` secret.

A normal green workflow does **not** claim that the registered-key live 10+10 soak ran. That job remains visibly skipped unless explicitly selected with a newly rotated repository secret.

Do not paste a key into a workflow input, issue, pull request, source file or chat. Add it directly through the encrypted secret settings of the service that needs it.

## Deployment note

Production remains public and deliberately uses NASA's `DEMO_KEY` until higher limits are genuinely necessary. For higher limits, configure a newly rotated `NASA_API_KEY` in Vercel's encrypted Environment Variables settings and redeploy. Do not commit a production `.env` file.

See [`hosted/README.md`](hosted/README.md) for the exact product boundary, checks, quota controls and deployment procedure.
