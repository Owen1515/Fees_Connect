# Render fix validation: 27 September 2026

This record separates completed local checks from target-environment checks.
The project was tested with its existing locked dependencies on Python 3.12.14.

| Check | Result |
| --- | --- |
| Existing application tests plus 23 deployment regressions | **105 passed, 1 skipped** |
| Application line coverage | **89.14%**, required threshold 85% |
| Skipped check | PostgreSQL-specific concurrent payment row-lock test |
| Production settings | Valid Render-format key accepted; missing/weak/sample keys rejected |
| Existing long secret | Preserved byte-for-byte; no automatic rotation |
| Microsoft settings | Missing client ID fails; no credential printed in error |
| Hostname, origins and HTTPS | Allocated Render hostname admitted, secure route redirect retained |
| Health endpoints | HTTP liveness succeeds; unavailable DB gives 503 readiness |
| Render Blueprint | Validated against Render's official JSON Schema retrieved 27 September 2026 |
| Shared settings | Web/worker/beat secrets, OAuth, URLs and datastore references checked |
| Static build | Exact Docker collectstatic command passed with runtime credentials blank |
| Fresh migrations/bootstrap | Passed on a temporary SQLite database |
| Deployment system checks | `check --deploy --fail-level WARNING` passed with isolated test configuration |
| Local process smoke | Gunicorn bound supplied PORT and served home/login/static CSS |
| Local Celery smoke | Worker answered control ping and completed an empty-outbox task through Redis 6.2.14 |
| Local Beat smoke | Scheduler started successfully |
| PDF smoke | WeasyPrint generated a valid PDF using local native libraries |
| Schema drift | `makemigrations --check --dry-run`: no changes |
| Code quality | Black, isort, Ruff passed |
| Installed dependency compatibility | `pip check` passed |

## Scope of the local process smoke

The smoke harness imported and validated production settings using temporary,
non-production values, then substituted SQLite solely as its test database.
Gunicorn, Celery and Redis ran as real local processes. No production database,
Microsoft tenant or payment provider was contacted. The test-only override and
its temporary credentials are not shipped as an application runtime profile.

This proves process wiring, static delivery and local broker/task behaviour. It
is **not** a PostgreSQL transaction test, an actual Docker build, or a Render
account deployment. Redis 6.2.14 was the locally available test binary; CI uses
Redis 7 and Render uses its managed compatible service.

Docker and PostgreSQL were unavailable in this execution environment. The
updated `.github/workflows/tests.yml` includes both the existing PostgreSQL 16
suite and a Docker-image smoke job with PostgreSQL 16 and Redis 7. That job builds
the image, runs release migrations, starts all three roles, checks readiness,
static files, native PDF dependencies and Celery. **Those CI jobs were added but
have not been run from this workspace.**

## Still requires the user's environment

- Run the GitHub Actions jobs and a real Render build/deploy.
- Confirm existing resource regions and the actual web-service command/commit.
- Supply valid production secrets and Microsoft OAuth tenant/application values.
- Test SMTP permissions and message delivery to a real approved test recipient.
- Test live-target PostgreSQL/Redis connectivity and backup restoration.
- Verify client-IP attribution/throttling through the actual edge proxy.
- Complete merchant onboarding and the previously documented provider capability
  work before enabling payments.

The complete pytest output is in `TEST_RESULTS.txt`; current machine-readable
coverage is in `coverage.json`. No claim of complete production certification is
made by these local test results.
