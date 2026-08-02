# NASA Open APIs integration

This connector exposes a small dependency-free Python interface for:

- Astronomy Picture of the Day (`apod`)
- Near-Earth Objects (`near_earth_objects`)
- DONKI space-weather events (`space_weather`)

## Secret setup

The client reads `NASA_API_KEY` from the environment. Never commit the real key.

```bash
export NASA_API_KEY="your-rotated-key"
python integrations/nasa/nasa_client.py
```

For PowerShell:

```powershell
$env:NASA_API_KEY = "your-rotated-key"
python integrations/nasa/nasa_client.py
```

Because a key was shared in chat before this integration was committed, rotate that key first and use the replacement locally or in the deployment platform's encrypted secrets settings.

## Example

```python
from datetime import date
from integrations.nasa.nasa_client import apod, near_earth_objects, space_weather

picture = apod()
asteroids = near_earth_objects(date.today())
solar_flares = space_weather("FLR", date(2026, 8, 1), date(2026, 8, 2))
```

NASA's current Open APIs catalogue documents APOD, NeoWs and DONKI. The older Earth and Mars Rover catalogue endpoints are archived, so this connector intentionally avoids them.
