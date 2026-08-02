# NASA Data Hub

A standalone Python dashboard and command-line client for selected public NASA APIs and NASA EONET.

> Independent open-source project by Luca Panayiotou. Not affiliated with, endorsed by, or operated by NASA.

## What it does

- Serves a local browser dashboard.
- Keeps the API key on the Python server rather than in browser JavaScript.
- Supports Astronomy Picture of the Day (APOD).
- Supports near-Earth-object feeds, lookup and browsing.
- Supports DONKI space-weather events.
- Supports EONET natural-event data without sending an API key.
- Provides a dependency-free Python client and CLI.
- Adds bounded retry/backoff, safe caching, rate-limit metadata and actionable errors.
- Works immediately with NASA's limited public `DEMO_KEY`.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .
python -m nasa_data_hub health
python -m nasa_data_hub serve --open
```

The dashboard opens at `http://127.0.0.1:8765`.

You can also use the included launchers:

```powershell
.\start.ps1
```

```bash
chmod +x start.sh
./start.sh
```

## API-key handling

The application falls back to NASA's public `DEMO_KEY` when `NASA_API_KEY` is empty. For higher limits:

1. Generate a new key through NASA's official API portal.
2. Copy `.env.example` to `.env`.
3. Put the key only in the local `.env` file or a hosting provider's encrypted secret store.

Never paste a real key into source, issues, pull requests, workflow inputs or browser code. A key previously shared in chat must be treated as exposed and rotated.

## Commands

```bash
nasa-data-hub health
nasa-data-hub doctor
nasa-data-hub serve --open
nasa-data-hub apod --date 2026-08-02
nasa-data-hub neo --start 2026-08-02 --end 2026-08-05
nasa-data-hub neo-lookup 3542519
nasa-data-hub neo-browse --page 0 --size 20
nasa-data-hub donki FLR --start 2026-08-01 --end 2026-08-02
nasa-data-hub eonet --status open --days 14 --category wildfires
```

## Verification

The source state used for this standalone export completed:

- the offline unit suite on Python 3.10, 3.11, 3.12 and 3.13;
- 15 consecutive clean build/install/runtime cycles on Linux;
- 15 consecutive clean build/install/runtime cycles on Windows;
- zero failures in those 30 NASA cycles.

Every clean cycle compiled the package, ran the offline tests, validated the OS launcher, built a wheel, created a fresh environment, installed the wheel, checked the installed command, started the packaged server with deterministic upstream fixtures, exercised the dashboard and every local API route, and checked expected error responses.

See [`docs/TEST_EVIDENCE.md`](docs/TEST_EVIDENCE.md). These results prove the tested deterministic software paths for the recorded source state. They do not prove that external services will never be unavailable or that an undiscovered defect is impossible.

A separate registered-key live soak exists but is not counted as completed until it runs using a newly rotated repository secret.

## Test locally

```bash
python -m compileall -q nasa_data_hub
python -m unittest discover -s tests -v
python scripts/reliability_gate.py --phase 1 --passes 1
```

## Project structure

```text
nasa_data_hub/       Python package, server, CLI and browser dashboard
scripts/             deterministic and live reliability probes
tests/               offline unit tests
docs/                evidence and operating notes
.github/workflows/   test and reliability gates
```

## Security boundary

- The browser communicates only with the local Python server.
- The server adds the key only to authenticated `api.nasa.gov` requests.
- EONET requests never receive the key.
- Cache identities are built from URLs with the secret excluded.
- `.env`, private keys, caches, builds and virtual environments are ignored.
- Real live-soak credentials must come from the process environment or GitHub Actions secrets.

See [`SECURITY.md`](SECURITY.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
