# NASA data integration

A secure, dependency-free Python client and CLI for useful NASA data sources.

## Included capabilities

### NASA Open APIs (`api.nasa.gov`)

- APOD: one date, date ranges, and random selections
- NeoWs: near-Earth-object date feed, asteroid lookup, and dataset browsing
- DONKI: CME, CME analysis, geomagnetic storms, interplanetary shocks, solar flares, solar energetic particles, magnetopause crossings, radiation-belt enhancements, high-speed streams, WSA-Enlil simulations, and notifications
- NASA rate-limit header tracking
- Retry handling for HTTP 429 and temporary 5xx failures
- Optional local response caching

### EONET v3

- Open, closed, or all natural events
- Category and source filtering
- Date/day filtering
- Bounding-box queries
- Standard JSON or GeoJSON
- Individual events, categories, sources, and imagery layers

EONET is unauthenticated, and the client deliberately does **not** send the NASA API key to its separate host.

## Security first

A NASA key was originally supplied in chat. Treat that key as exposed and rotate it before use.

The real key must never be placed in source code, `.env.example`, commits, issues, logs, screenshots, or command history shared publicly. Store the replacement in a local or deployment secret store under:

```text
NASA_API_KEY
```

The repository already ignores `.env`, `.env.local`, `.env.*.local`, `credentials.json`, and `secrets.txt`.

### Linux/macOS

```bash
export NASA_API_KEY="your-rotated-key"
```

### PowerShell

```powershell
$env:NASA_API_KEY = "your-rotated-key"
```

For persistent deployment, use the encrypted environment-variable or secrets settings provided by the host rather than committing a file.

## CLI

After installing the project:

```bash
python -m pip install -e .
```

The following command becomes available:

```bash
the-well-nasa --help
```

### Astronomy Picture of the Day

```bash
the-well-nasa apod

the-well-nasa apod --date 2026-08-02

the-well-nasa apod --start 2026-08-01 --end 2026-08-02

the-well-nasa apod --count 5
```

### Near-Earth objects

```bash
the-well-nasa neo --start 2026-08-02 --end 2026-08-05

the-well-nasa neo-lookup 3542519

the-well-nasa neo-browse --page 0 --size 20
```

NeoWs date-feed windows are validated at a maximum of seven days.

### Space weather

```bash
the-well-nasa donki FLR --start 2026-08-01 --end 2026-08-02

the-well-nasa donki CME --start 2026-08-01 --end 2026-08-02

the-well-nasa donki notifications --start 2026-08-01 --end 2026-08-02
```

### Natural events

```bash
the-well-nasa eonet --status open --limit 20

the-well-nasa eonet --days 14 --category wildfires

the-well-nasa eonet --source InciWeb --geojson
```

Use `--compact` before the subcommand for compact JSON. Use `--cache-dir PATH` before the subcommand to cache cacheable responses.

## Python API

```python
from datetime import date

from integrations.nasa import NASAClient

client = NASAClient.from_env(
    cache_dir=".cache/nasa",
    cache_ttl_seconds=300,
)

picture = client.apod(day=date(2026, 8, 2))
asteroids = client.neo_feed(date(2026, 8, 2), date(2026, 8, 5))
flare_events = client.donki(
    "FLR",
    start_date=date(2026, 8, 1),
    end_date=date(2026, 8, 2),
)
wildfires = client.eonet_events(
    status="open",
    categories=["wildfires"],
    days=14,
)

print(client.rate_limit.limit, client.rate_limit.remaining)
```

Additional methods:

```python
client.apod(start_date=..., end_date=...)
client.apod(count=5)
client.neo_lookup("3542519")
client.neo_browse(page=0, size=20)
client.donki_notifications(start_date=..., end_date=...)
client.eonet_event("EONET_1234")
client.eonet_categories()
client.eonet_sources()
client.eonet_layers("wildfires")
```

## Failure behaviour

`NASAAPIError` includes `status_code` and `retry_after` when provided by the server. HTTP 429 and temporary 5xx responses are retried with bounded backoff. Invalid parameter combinations fail before making a network request.

NASA's default registered-key limit is currently 1,000 requests per hour across `api.nasa.gov`; exact service limits can vary. The latest returned values are available through `client.rate_limit`. EONET uses a separate unauthenticated service.

## Tests and CI

Local test command:

```bash
python -m pytest -q tests/integrations/test_nasa_client.py
```

The dedicated GitHub Actions workflow compiles the client and runs the integration tests on Python 3.10, 3.11, 3.12, and 3.13 whenever relevant files change.

## Official references

- NASA Open APIs: https://api.nasa.gov/
- EONET v3 documentation: https://eonet.gsfc.nasa.gov/docs/v3

The archived Earth and Mars Rover catalogue endpoints are intentionally not used. NASA currently directs Earth imagery users to Earthdata GIBS instead.
