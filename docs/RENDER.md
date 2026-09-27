# FeesConnect on Render: corrected full project

Use the complete contents of this project folder. This replaces the earlier
three-file overlay. The uploaded source was inspected directly; no AltraSure or
Travold application files are changed.

## What caused the failure

Your traceback is from `/app` and `/usr/local/lib/python3.12`, matching the Docker
image. The uploaded `render.yaml` instead selected `runtime: python`. Docker does
not run that YAML's native build/start commands, so changing only the YAML did not
necessarily change the service already configured in the dashboard.

The immediate crash was the production secret length guard. Render generates a
base64-encoded 32-byte random value (44 characters). The old guard demanded 50
characters. That is a length-format mismatch, not evidence that Render's generated
256-bit secret is weak.

The corrected production code recognises that precise format and losslessly
re-encodes its 32 bytes as 64 hex characters. No entropy is added or removed and
no new key is generated on boot. Every service gets the same stable result.
Existing valid 50+ character secrets remain unchanged. Missing, short, repeated
and known placeholder values still fail. Do not change a working long key or an
existing data encryption key during this update.

## Apply to the service you already created

1. Extract this ZIP. Upload/commit the **contents of `Fees-Connect-main/`** to the
   repository root where `manage.py` currently lives. Include the updated
   `Dockerfile`, `render.yaml`, `config/deployment.py`, `config/settings/`,
   `config/celery.py`, `deployment/start.py`, and the new management command.
   Do not leave the old versions alongside the new project in an extra folder.
2. Inspect the actual regions of your existing database and Key Value instance.
   The old YAML omitted their regions, which default to Oregon, while the web
   services specified Frankfurt. Internal URLs require a common region. The new
   Blueprint describes Frankfurt throughout. Existing regions cannot be changed
   in place: if the stores are elsewhere, align the application/resources through
   a planned migration rather than deleting data. Confirm this before syncing.
3. If using an existing Blueprint, sync it after entering the Microsoft values
   below. If using manually created services, update their dashboard settings
   directly using the following table. Merely pushing `render.yaml` does not make
   an ordinary service Blueprint-managed.
4. Preserve resource names and inspect the Blueprint preview before applying it.
   Do not create another empty database by accidentally deploying a second stack.
   Compute plans are omitted so existing plans are retained; new resources use
   paid defaults. The web pre-deploy task and background workers need paid compute.
5. Clear any old Docker command override in Render or replace it with the command
   below. The traceback suggests that your existing Docker command was still
   starting Gunicorn directly.

| Setting | Web | Worker | Beat |
| --- | --- | --- | --- |
| Runtime/Language | Docker | Docker | Docker |
| Dockerfile path | `./Dockerfile` | `./Dockerfile` | `./Dockerfile` |
| Docker build context | `.` | `.` | `.` |
| Docker command | `python deployment/start.py web` | `python deployment/start.py worker` | `python deployment/start.py beat` |
| Pre-deploy command | `python deployment/start.py release` | none | none |
| Health check | `/readyz/` | none | none |
| Instances | initially 1 | initially 1 | exactly 1 |

There is no native Python build command in this Docker setup. Render uses the
Dockerfile to install requirements and collect static assets. Keep the Git branch
consistent with your repository. No dependency-version change is required for the
reported error.

## Required environment variables

The Blueprint creates/reuses PostgreSQL and Key Value references. It generates
Django/data keys if they are absent and shares the web service's environment with
worker and beat. For an existing Blueprint, `sync: false` values must be entered
manually. Changes to referenced web values propagate on the next Blueprint sync;
verify and redeploy all three services after changing credentials.

| Variable | What to supply |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` on all three services |
| `DJANGO_SECRET_KEY` | Keep the existing Render-generated key or your existing long random key |
| `DATA_ENCRYPTION_KEY` | Keep the existing valid Fernet key; generate one only if absent |
| `DATABASE_URL` | The correct database's same-region internal connection URL |
| `REDIS_URL` | The correct Key Value instance's same-region internal connection URL |
| `MS_TENANT_ID` | Real Microsoft Entra tenant ID |
| `MS_CLIENT_ID` | Real app registration/application ID |
| `MS_CLIENT_SECRET` | Real client secret **value**, not the secret's ID |
| `EMAIL_HOST_USER` | `support@feesconnect.com`, after the mailbox exists |
| `DEFAULT_FROM_EMAIL` | `FeesConnect <support@feesconnect.com>` |
| `SUPPORT_EMAIL` | `support@feesconnect.com` |
| `SITE_URL` | The actual web service HTTPS URL; Blueprint references `RENDER_EXTERNAL_URL` |
| `DJANGO_ALLOWED_HOSTS` | `feesconnect.com,www.feesconnect.com`; the real Render hostname is added automatically |
| `CSRF_TRUSTED_ORIGINS` | `https://feesconnect.com,https://www.feesconnect.com`; the Render origin is also added |
| `TRUST_PROXY_HEADERS` | `false` on Render; the former setting assumed your own Nginx |
| `PAYMENTS_ENABLED` | `false` until merchant/provider acceptance is complete |
| `PAYMENT_ENVIRONMENT` | `test` during setup |

To generate a Django key locally if none exists:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

To generate a data encryption key locally, with project dependencies installed:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put generated values into Render Environment, never the source code or Docker
build arguments. Do not generate different keys on each service. Changing the
Django key invalidates sessions/signatures; replacing the data encryption key
makes existing encrypted outbox/provider data unreadable.

Production still requires real Microsoft OAuth configuration. The code does not
invent credentials, send through a dummy backend, or silently enable development
settings. If the mailbox/app is not ready, complete `docs/MICROSOFT_365.md` before
expecting account verification, password reset or receipt delivery. Startup
validates presence; it cannot prove the credentials and SMTP grants are correct.

## Build and startup behaviour

- The Docker image installs Pango, fonts and HarfBuzz subset support for PDFs.
- Static assets are collected using `config.settings.build`, with no database,
  SMTP or production secrets. That profile is for collection only and is rejected
  by the runtime launcher. Never select it in the Render dashboard.
- The release command validates production settings, waits for PostgreSQL/Redis,
  and applies migrations once. Web/worker/beat do not each run migrations.
- Runtime services wait for the database, cache and committed migrations, then
  start. This prevents a worker from querying absent tables during the first
  deployment. A bounded timeout reports the failing stage without dumping secrets.
- Gunicorn binds `0.0.0.0:$PORT`, using 8000 only outside Render when PORT is absent.
- Celery defaults to production if no settings module is explicitly supplied;
  `manage.py` still explicitly selects development for local commands.
- `/healthz/` reports process liveness. `/readyz/` checks DB/cache. Those two status
  paths bypass Django's HTTPS redirect; application routes retain HTTPS and secure
  cookies. Render's edge normally terminates TLS.
- Redis eviction is disabled for the Celery broker. Monitor memory and capacity.
  Keep beat at one instance; rolling deploys can still briefly overlap schedulers,
  so task/payment idempotency remains essential.

After the first successful release, run these in the web service's Render shell:

```bash
python manage.py bootstrap
python manage.py createsuperuser
```

Bootstrap creates reference currencies, roles and the initial 3% policy. It does
not create live merchant accounts or approve schools. Enrol the operator in 2FA.
Then run `python manage.py send_test_email --help` and use the documented command
for an existing test user. Check Celery logs and that the queued message arrives.

## If it still fails, use the new error to identify the missing input

| Symptom | Next action |
| --- | --- |
| Old `at least 50 characters` exception at old `prod.py` line 9 | Render built an old commit/folder/image. Check its deployed commit, root directory and Dockerfile path, then rebuild. The revised exception text is different. |
| `DJANGO_SECRET_KEY is missing or unsafe` | The running service has no usable key, or a placeholder was preserved. Enter a real key on all three services. |
| `Production configuration: ...` | Supply the listed environment variables. Multiple missing values are reported together. |
| Startup waits/times out | Check datastore region, internal URLs, database permissions, and web pre-deploy migration logs. |
| `DisallowedHost` | Check the actual hostname and `DJANGO_ALLOWED_HOSTS`; use no wildcard. |
| Static files return 404 | Confirm the corrected Docker build ran collectstatic and no stale volume/STATIC_ROOT hides `/app/staticfiles`. |
| Worker ready but mail retries/dead-letters | Complete Microsoft OAuth and SMTP mailbox permissions, then replay/retry as documented. |

## Deployment limits and data handling

The full application suite and the new deployment regression tests are recorded
in `docs/RENDER_VALIDATION.md`. These tests do not prove your Render account,
Microsoft tenant or payment-provider configuration.

Render's ordinary filesystem is ephemeral. Existing receipts are regenerated
from their database snapshot if their cached PDF is absent; their local PDF files
are not an archival store. For regulated/permanent PDF retention and shared
private uploads, add private object storage before launch. The current project
has no public media route. Back up PostgreSQL and exercise restore procedures.

Before public launch, verify client-IP attribution/throttles through Render's
actual edge, a complete email flow, a PDF receipt, and payment sandboxes. The
VPS-specific X-Real-IP trust was removed from Render; no arbitrary forwarded
client-IP header is trusted by the custom middleware. This fix does not complete
outstanding Paynow split/refund or executable FX provider implementations.

After verifying your custom domains in Render, change the web `SITE_URL` entry
from its self-reference to `value: https://feesconnect.com`, sync, then redeploy
web/worker/beat. This source update does not change DNS or create a certificate.

## Official references

- [Docker on Render](https://render.com/docs/docker)
- [Blueprint specification](https://render.com/docs/blueprint-spec)
- [Environment variables](https://render.com/docs/configure-environment-variables)
- [Private networking and regions](https://render.com/docs/private-network)
- [Health checks](https://render.com/docs/health-checks)
