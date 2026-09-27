# Changes made to the uploaded FeesConnect project

| File or area | Defect found | Correction |
| --- | --- | --- |
| `config/deployment.py`, `config/settings/prod.py` | The 50-character guard rejected Render's 44-character encoding of a 256-bit random key | Validate the exact 32-byte base64 format and losslessly convert it to 64 hex characters; preserve existing long keys; reject empty/weak/sample inputs |
| `render.yaml` | Native Python configuration conflicted with Docker runtime logs | Use Docker consistently for web, worker and beat |
| `render.yaml` | Web Redis reference used invalid `kvStore` type | Use `keyvalue` consistently |
| `render.yaml` | Worker/beat lacked encryption, OAuth and public URL values | Reference the corresponding web environment values on both worker services |
| `render.yaml` | DB/Redis region omitted while web was Frankfurt | Describe a common region; document that existing resources need inspection/migration rather than an in-place region change |
| `Dockerfile`, `config/settings/build.py` | Image never collected WhiteNoise assets; production collection required runtime credentials | Collect manifest static assets with a dedicated build-only profile; no production secrets used in image layers |
| `Dockerfile` | Native PDF dependencies incomplete for newer WeasyPrint behaviour | Add HarfBuzz subset support alongside Pango and fonts |
| `deployment/start.py` | Docker CMD hardcoded port 8000 and launched Gunicorn directly | Honour PORT and configurable concurrency; use one shell-free launcher with proper process replacement |
| `deployment/start.py`, `wait_for_services` | No bounded database/cache/schema startup gate | Wait before accepting traffic or starting workers; fail with actionable, redacted errors |
| Release command/Blueprint | Migrations mixed into native build and no Docker migration path | Run one pre-deploy release command; never race migrations from each replica |
| `config/celery.py` | Importing config could default the process to dev before WSGI set prod | Default server/Celery imports to production; retain explicit local manage.py dev behaviour |
| Production settings | Hardcoded/guessed Render hostname and ignored/mismatched origins | Use actual Render hostname/public URL and explicit custom-domain origins |
| Production settings | Production validation only checked part of OAuth configuration | Check all required OAuth identifiers and Fernet format; report missing values together |
| Production settings | Nginx X-Real-IP assumption carried into Render | Default that custom-header trust off; keep explicit opt-in for the documented VPS Nginx |
| Health checks | Admin login used as health check; HTTP redirects could count as healthy | Use DB/cache readiness and exclude only status paths from the Django HTTPS redirect |
| `.dockerignore`, `.gitignore` | `.env.production` and `.env.database` could enter image context or source commits | Exclude runtime environment variants, private keys, local database/cache/generated files |
| `docker-compose.yml` | Static volume could mask updated image assets | Use image assets; route production worker commands through the same launcher |
| Tests/CI | No regression coverage for Render settings or Docker startup | Add 23 regression tests and a Docker/PostgreSQL/Redis CI smoke job |
| README/docs/editor settings | No full existing-Render recovery instructions | Add Render setup, change log, validation record and YAML schema assistance |

All existing business models, migrations, templates, frontend assets and gateway
business logic are retained. New deployment code is commented and uses typed
interfaces where it exposes functions. Runtime credentials remain external.
