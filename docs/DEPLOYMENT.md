# Ubuntu VPS deployment

Use Ubuntu 24.04 LTS for its Python 3.12 and PostgreSQL 16 packages. Ubuntu 22.04 is possible only after installing a maintained Python 3.12 runtime and PostgreSQL 16 from trusted repositories. Do not run this project with the older default Python on 22.04.

## 1. DNS and system packages

In Namecheap Advanced DNS, set A records for `@` and `www` to the VPS IPv4 address. Remove conflicting parking records. Set AAAA only if IPv6 is actually configured. These changes are operator actions; this source package does not change DNS.

```bash
sudo apt update
sudo apt install python3.12-venv postgresql-16 redis-server nginx certbot ufw fail2ban libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core
sudo adduser --system --group --home /srv/feesconnect feesconnect
sudo mkdir -p /srv/feesconnect/releases /var/lib/feesconnect/private /var/www/feesconnect/static /var/www/certbot /var/backups/feesconnect
sudo chown -R feesconnect:feesconnect /srv/feesconnect /var/lib/feesconnect /var/www/feesconnect /var/backups/feesconnect
```

## 2. PostgreSQL and Redis

Use a dedicated PostgreSQL login. Open `sudo -u postgres psql` and run:

```sql
CREATE ROLE feesconnect LOGIN;
\password feesconnect
CREATE DATABASE feesconnect OWNER feesconnect;
```

Use the interactive password command rather than placing a password in shell history. Restrict PostgreSQL to localhost and SCRAM authentication. Redis must be bound to loopback with protected mode; do not expose port 6379. For stricter operations, separate the migration owner from the runtime database role and grant only required table/sequence privileges. The application has no need for PostgreSQL superuser access.

## 3. Release directory and protected environment

Copy the unpacked project to a timestamped directory under `/srv/feesconnect/releases/`. Build its venv and install the lock file as the service user. Point `/srv/feesconnect/current` to that release. Preserve old releases for rollback.

Create `/etc/feesconnect.env`, owned by root and readable by the service group only (`0640`, group feesconnect). Set all values from .env.example, including:

- DJANGO_SETTINGS_MODULE=config.settings.prod
- DJANGO_ALLOWED_HOSTS=feesconnect.com,www.feesconnect.com
- SITE_URL=https://feesconnect.com
- DATABASE_URL for the dedicated PostgreSQL login
- a strong DJANGO_SECRET_KEY and generated DATA_ENCRYPTION_KEY
- TRUST_PROXY_HEADERS=true only for the supplied private Nginx configuration
- Redis, Microsoft OAuth and Sentry settings
- STATIC_ROOT=/var/www/feesconnect/static
- PRIVATE_ROOT=/var/lib/feesconnect/private
- PAYMENTS_ENABLED=false until acceptance is complete

Systemd EnvironmentFile syntax differs from shell syntax: quote values containing spaces. Never commit the file. Store encryption keys separately from backups. Encrypt database/private volumes and backup media; django-otp's device/recovery material additionally relies on those storage protections. Rotate credentials using provider-supported overlap windows.

Using that protected environment, run as the service user:

```bash
python manage.py migrate --noinput
python manage.py bootstrap
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py createsuperuser
```

Production settings intentionally refuse SQLite or missing encryption/OAuth credentials. The initial operator enrols 2FA before entering admin.

## 4. HTTPS and Nginx

Start with deployment/nginx-bootstrap.conf as the site's Nginx configuration. Test with `sudo nginx -t`, then reload. Issue certificates:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d feesconnect.com -d www.feesconnect.com
```

Install deployment/nginx.conf after the certificate exists. Test/reload Nginx again and run `sudo certbot renew --dry-run`. Nginx terminates TLS and connects to Gunicorn over a Unix socket. It overwrites forwarding headers. Do not expose Gunicorn directly to the internet. Static files come from `/var/www/feesconnect/static/`; private receipts and invoices have no Nginx alias.

## 5. Gunicorn and Celery

Copy deployment/systemd/*.service and *.timer into `/etc/systemd/system/`. Make deployment/backup.sh executable. Ensure the service group can read the environment and socket. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now feesconnect feesconnect-worker feesconnect-beat
sudo systemctl status feesconnect feesconnect-worker feesconnect-beat
```

Run one beat service. Celery workers and Gunicorn need the same settings, database, encryption key and private-file storage. SMTP tasks are bounded and retry through the outbox; dead-letter rows need operator attention.

## 6. Firewall, SSH and monitoring

Before enabling UFW, ensure SSH key access works in another terminal:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo systemctl enable --now fail2ban
```

Enable the sshd jail in `/etc/fail2ban/jail.d/sshd.local`. Disable password SSH login after validating key access. If using a nonstandard SSH port, adjust these commands first.

Set SENTRY_DSN and test a controlled non-sensitive exception. Monitor `/healthz/` for process liveness and `/readyz/` for database/cache readiness. Also monitor queue age, dead letters, unknown payment outcomes, unresolved reconciliation differences, failed mail, backup age, certificate expiry and disk space. A healthy web process does not prove a worker is delivering messages.

## 7. Backups and restore

Give the backup user a protected `.pgpass` (`0600`); never place the DB password in backup command arguments. Enable `feesconnect-backup.timer`. The script creates custom-format pg_dump files, checks their table of contents and retains 30 days. Copy encrypted backups and private documents to offsite storage with separate access credentials.

Practise restoration into a separate database with `createdb` and `pg_restore --no-owner --dbname=restore_test backup.dump`. Reconcile row counts, invoice balances, payment/refund totals and receipt files before declaring the backup usable. Back up private storage and preserve encryption keys separately. Never restore over live data as an unreviewed routine action.

## 8. Release and rollback

For an ordinary maintenance deployment, stop new checkouts, drain in-flight requests, stop beat, allow active workers to finish, take a backup, apply compatible migrations, switch the release symlink and restart web/worker/beat services. Confirm readiness and resume collection. This procedure has a maintenance window.

For deployments requiring zero request downtime, use blue/green Gunicorn services on distinct sockets. Stage the new release, apply only expand-compatible migrations, start the green service, verify its readiness, change the Nginx upstream to green, test/reload Nginx, then drain blue. Keep old workers running only for backwards-compatible task payloads. Switch singleton beat once. Do not assume HUP changes an already-running process's release directory. The included single-service file is not itself a blue/green orchestrator.

Rollback application code by switching traffic back to the retained healthy release while schema remains compatible. Do not blindly reverse destructive migrations or replay payments. Data recovery requires a separate plan and provider reconciliation. Defer contract/drop migrations until the rollback window expires.

## 9. Docker alternative

Use docker-compose.yml with protected `.env.production` and `.env.database` files. Production DATABASE_URL must address the `db` service and REDIS_URL the `redis` service. Bind only the web port to loopback behind host Nginx. Run `docker compose run --rm web python deployment/start.py release` and then `docker compose run --rm web python manage.py bootstrap` before starting production traffic. Static files are collected into the image at build time; an existing static volume must be refreshed with collectstatic if retained. Configure Nginx to serve the collected static volume or allow WhiteNoise to serve `/static/`. Do not use the development Compose password or runserver in production.

## Launch checklist

- [ ] Real legal entity and school approvals verified.
- [ ] Provider accounts and country/currency eligibility confirmed.
- [ ] School principal and FeesConnect fee split verified on actual provider statements.
- [ ] Paynow split/refund contract and FX adapter implemented if those routes will be offered.
- [ ] 3% cost coverage and refund commercial policy signed off.
- [ ] Stripe/PayPal/Paynow sandbox callbacks, duplicates, timeouts, refunds and pending cases tested with real provider credentials.
- [ ] Mailbox created; OAuth2, SPF/DKIM/DMARC and actual receipt delivery tested.
- [ ] PostgreSQL concurrency suite, target browser/mobile layout checks and security review completed.
- [ ] Terms/privacy/contact details approved for the operating business.
- [ ] HTTPS redirect, renewals, 2FA, firewall and SSH verified.
- [ ] Backups restored successfully in an isolated environment.
- [ ] Sentry, uptime and worker/reconciliation alerts verified.
- [ ] No demo credentials, sample merchant IDs or unapproved routes enabled.
