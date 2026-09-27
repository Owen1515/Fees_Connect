# FeesConnect Django

**Deploying on Render? Start with [docs/RENDER.md](docs/RENDER.md).**
This revision fixes the generated-secret boot failure and uses one Docker deployment
path for web, worker and beat. Push the complete folder contents, including the updated
`Dockerfile`, `render.yaml`, `config/` and `deployment/`, then update the existing
Render service commands as documented. Runtime credentials still belong in Render.


A standalone FeesConnect project for Python 3.12 and Django 5.2.17. Open **feesconnect.code-workspace** or the folder containing **manage.py** in VS Code. No Travold or AltraSure implementation is included or changed.

## Start locally

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py bootstrap
python manage.py createsuperuser
python manage.py runserver
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py bootstrap
python manage.py createsuperuser
python manage.py runserver
```

In VS Code, choose the project's `.venv` with **Python: Select Interpreter**, then press F5. The checked-in interpreter hint uses Linux paths; Windows users select `.venv\Scripts\python.exe`. The application opens at http://127.0.0.1:8000/. There is no default production password. Create your own operator with createsuperuser and enrol 2FA on first use.

For PDF generation, install WeasyPrint system dependencies. On Ubuntu 24.04 use `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core`. On Windows, use the Docker option or follow WeasyPrint's Windows/MSYS2 setup. The web app can run without producing PDFs until those dependencies are available.

One-command local PostgreSQL/Redis alternative: `docker compose -f docker-compose.dev.yml up --build`. Then run `docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser`. This Compose file is local development only.

## Local email and background jobs

Development uses console email. Register a parent/student, then run `python manage.py process_jobs` in another terminal to print the verification email. Follow its URL and submit the confirmation form. Repeat process_jobs for password-reset emails and queued payment work. An HTML request does not synchronously send email.

For continuous local workers, start Redis, then explicitly select development settings:

```bash
DJANGO_SETTINGS_MODULE=config.settings.dev celery -A config worker -l INFO
DJANGO_SETTINGS_MODULE=config.settings.dev celery -A config beat -l INFO
```

On Windows PowerShell, first set `$env:DJANGO_SETTINGS_MODULE="config.settings.dev"` in each terminal, then run the corresponding `celery` command without the Unix prefix.

Run exactly one beat scheduler per deployment. Production must run both services. Redis connection details come from REDIS_URL.

## What is included

- Seven namespaced Django apps: accounts, fees, payments, dashboard, support, core and api.
- Custom email user model, multi-role assignments, verified pupil links, school approval, password reset, TOTP and single-use recovery codes.
- All 12 uploaded HTML filenames mapped to Django routes, retained brand assets and a separate original demo.
- Thirty-nine business models, committed migrations, field help text and a generated database schema document.
- Full/partial fee payments with one 3% combined charge, server-side quotes, idempotency, balance reservations and provider-confirmed allocation.
- Registered Stripe, PayPal and Paynow adapters, signed webhooks, asynchronous initiation, retry-safe reconciliation, private invoices/receipts and PDF email attachments.
- OAuth2 SMTP backend for the future support@feesconnect.com mailbox, branded HTML/plain-text emails and a test-email command.
- Stable authenticated `/api/support/chat/`, curated FAQ responses and support tickets. This is a deterministic support assistant, not an external generative model.
- Pupil and settlement CSV import tools, import templates, audit records, reference-data bootstrap and webhook replay command.
- PostgreSQL 16/Redis deployment configuration, Nginx, systemd, Docker alternatives, backups, CI, tests and Postman collection.

## What requires external setup or further provider work

This source release is not evidence of live merchant approval or production acceptance. No provider accounts, mailbox, DNS records or VPS have been created. No real payment or email has been sent during development.

Stripe/PayPal require suitable registered merchant entities and approved connected-school/platform capabilities. Ordinary Paynow hosted checkout does not establish the requested automatic school/platform split: live Paynow collection is deliberately blocked pending its provider contract and corresponding split adapter. Its official SDK-based hosted/mobile sandbox flow is implemented. Paynow API refunds are likewise not invented; a documented merchant-specific refund interface is still required.

USD/ZWG/GBP/EUR fields and expiring FX-quote models are present. No existing provider agreement supplies an executable FX rate and guaranteed school proceeds. Cross-currency checkout is therefore disabled until an executable FX integration is supplied. Payer card issuers may perform their own conversion; that is not represented as a FeesConnect-guaranteed quote.

No additional charge beyond 3% is automatically added. The default is to disable a route whose estimated provider costs exceed the charge. The launch refund implementation refunds proportional customer charges. Confirm these commercial defaults before activating any live route.

Private statement imports support school/platform settlement reconciliation. The system does not claim that a capture means money has reached a school's bank. External dispute events and provider-originated refunds without a matching local request require finance review; the records exist but automated handling is not represented as complete.

Full browser visual acceptance and the PostgreSQL concurrency CI job must be completed in the target deployment environment. See docs/RENDER_VALIDATION.md for this revision and docs/VALIDATION.md for the original baseline.

## School onboarding

1. A verified user submits `/fees/schools/register/`.
2. A different platform operator checks the school and bank ownership.
3. Run `python manage.py approve_school SCHOOL_CODE --operator operator@example.com --admin-email schooladmin@example.com`.
4. Configure real MerchantAccount records through `/admin/`: one per school/gateway/currency plus a corresponding FeesConnect platform account. They remain pending until provider verification. Never use placeholder IDs as live accounts.
5. Assign per-school secret environment variable names, not secret values, in credential_secret_ref. Confirm fee incidence and method/currency capabilities with the provider.
6. School administrators verify student/guardian claims and issue invoices in `/fees/schools/manage/`.

Multiple roles are represented by RoleAssignment records. Group permissions define bundles; school and StudentAccess selectors still apply to every business request. The normal school administrator uses the school workspace, not cross-school Django admin.

## Payment configuration

Provider classes are registered in `apps/payments/services/gateways/__init__.py`. Set credentials only in environment configuration. `PAYMENTS_ENABLED=false` is the initial default. MerchantAccount environment must match PAYMENT_ENVIRONMENT. Do not mark split_verified without provider evidence.

A sample **sandbox capability record**, not a live contract:

```json
{"methods":["card"],"cost_rate":"0.02","cost_fixed":"0.00","split_verified":false}
```

The 2% value above is fictional test pricing, not a quotation from any gateway. Replace it with actual contracted pricing. Stripe direct-charge fee_bearer must be platform; Stripe connected-account fee incidence must match that configuration. PayPal platform fee is reduced by expected processor costs; actual statement differences are finance exceptions. Disable any live route without agreed net school settlement.

Stripe webhook: `/payments/webhooks/stripe/`.
PayPal webhook: `/payments/webhooks/paypal/`.
Paynow webhook: `/payments/webhooks/paynow/<merchant-uuid>/`.

Only webhook endpoints are CSRF-exempt, and they verify provider authenticity. The API uses same-origin session authentication plus CSRF, not permissive CORS/JWT. PayPal captures approved orders through the reconciliation worker. Mobile payments display Pending while the provider confirms. A five-minute scheduled reconciliation backs up callbacks.

## Data migration

Every field is implemented and enumerated in docs/DATABASE_SCHEMA.json. No actual school/student dataset was supplied. The provided CSV headers are migration contracts, not seeded personal records.

```bash
python manage.py export_schema > schema.json
python manage.py import_students students.csv --school SCHOOL_CODE --operator operator@example.com
python manage.py import_students students.csv --school SCHOOL_CODE --operator operator@example.com --commit
python manage.py import_settlements settlement.csv --operator operator@example.com
python manage.py import_settlements settlement.csv --operator operator@example.com --commit
```

Imports dry-run first. Pupil imports do not automatically link login accounts. Historical payments, fee schedules and invoice opening balances require mapping against the supplied future dataset before an importer is activated. Never import both a net opening balance and all historical payments as new allocations. No plaintext-password migration is supported.

## Development and testing

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
pytest
black --check .
isort --check-only .
ruff check .
pre-commit install
```

The pytest gate requires at least 85% line coverage across application code, excluding generated migrations. Test provider requests are mocked. PostgreSQL-only concurrent-payment tests are skipped on SQLite and run in the included PostgreSQL 16 CI job. tests/factories.py supplies factory-boy account fixtures.

## Documentation

- docs/PAGE_MAP.md: all existing and new pages, views and namespaced URLs.
- docs/DEPENDENCIES.md: pinned versions and provider references.
- docs/MICROSOFT_365.md: tenant, mailbox, OAuth2 and sender setup.
- docs/DEPLOYMENT.md: VPS, SSL, worker, backup, release and rollback instructions.
- docs/DATABASE_SCHEMA.json: every actual model field and relationship.
- docs/VALIDATION.md: executed results and unverified external dependencies.
- PROJECT_BRIEF.md: the historical Steps 1–2 design; implementation differences and commercial defaults in this README take precedence.
