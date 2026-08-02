# NASA integration moved

The maintained NASA integration now lives at:

```text
apps/nasa_data_hub/
```

That folder is intentionally standalone. It has its own package, browser dashboard, command-line interface, tests, launch scripts, `.env.example`, and CI workflow. It does not install or depend on the large root `the_well` package.

Existing Python imports through `integrations.nasa` remain available as a compatibility bridge, but new work should use:

```python
from nasa_data_hub import NASAClient, Settings
```

Run it from the standalone folder:

```powershell
cd apps/nasa_data_hub
.\start.ps1
```

See `apps/nasa_data_hub/README.md` for the complete setup and security guide.
