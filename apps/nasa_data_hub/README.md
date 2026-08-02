# NASA Data Hub

A standalone, understandable NASA integration that does **not** depend on the rest of `the_well`.

It provides:

- A local browser dashboard
- A safe server-side proxy, so the API key is never exposed to browser JavaScript
- Astronomy Picture of the Day
- Near-Earth-object approaches and asteroid lookup
- DONKI space-weather events
- EONET live natural events
- A command-line interface
- Retry handling, caching, rate-limit reporting, diagnostics, and tests
- A working out-of-box mode using NASA's public `DEMO_KEY`

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

When `NASA_API_KEY` is blank, the hub uses NASA's public `DEMO_KEY`. This has lower limits, but it means installation and the dashboard can be tested immediately.

Check configuration without making a network request:

```bash
python -m nasa_data_hub health
```

Test configuration and make a real APOD request:

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
│   └── static/          Browser dashboard assets
├── tests/               Offline unit tests
├── .env.example         Safe configuration template
├── start.ps1            Windows launcher
├── start.sh              macOS/Linux launcher
└── README.md            This guide
```

## Security

- Never commit `.env`.
- Never place the real key in HTML or frontend JavaScript.
- The dashboard talks only to the local Python server.
- The server adds the API key only to `api.nasa.gov` requests.
- EONET requests never receive the key.
- Cache filenames are derived from URLs with the secret removed.
- Error output does not include request URLs or API keys.

## Tests

From this folder:

```bash
python -m unittest discover -s tests -v
```

The repository workflow runs these tests on Python 3.10, 3.11, 3.12, and 3.13 without installing the large root project.

## Reliability gates

The `NASA Data Hub 20-pass reliability` workflow separates two kinds of evidence:

1. **Deterministic application reliability** runs automatically on relevant pull requests and pushes to `master`. Linux and Windows each perform ten complete passes followed by ten confirmation passes, covering build, clean installation, tests, startup and local route probes.
2. **Registered-key live API reliability** is a separate manual workflow option. It performs ten complete NASA API-family passes followed by ten confirmation passes and fails closed unless the repository has a newly rotated `NASA_API_KEY` secret.

A normal green workflow does **not** claim that the registered-key live 10+10 soak ran. In GitHub Actions, that job is visibly skipped unless **Run workflow → Run the registered-key NASA API 10+10 live soak** is selected.

Do not paste the key into a workflow input, issue, pull request or source file. Add it through **Repository Settings → Secrets and variables → Actions → New repository secret**, using the name `NASA_API_KEY`.

## Deployment note

For a hosted deployment, configure `NASA_API_KEY` using the hosting provider's encrypted secret/environment settings. Do not commit a production `.env` file.
