> Historical baseline. See [RENDER_VALIDATION.md](RENDER_VALIDATION.md) for the current Render fix and current test results.

# Validation report

Executed locally with Python 3.12.14 and Django 5.2.17.

| Check | Result |
| --- | --- |
| pytest | 82 passed, 1 skipped |
| Application line coverage | 89.19%; required gate 85% |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Fresh SQLite migrations | Applied successfully |
| Production settings check --deploy | No issues with temporary test configuration; no live services contacted |
| Black, isort and Ruff | Passed |
| Dependency consistency (pip check) | Passed |
| PDF generation | Real invoice/receipt PDFs generated and checked by tests |
| Provider and OAuth transports | Mocked; no live credentials used |
| Original CSS and brand asset integrity | Both original CSS files, PNG logo and favicon preserved byte-for-byte |

The skipped test requires PostgreSQL row locks. A PostgreSQL 16 CI workflow is included but was not executed in this environment. Run it before launch. The only pytest warning concerns a future WeasyPrint HarfBuzz system-library requirement; Ubuntu deployment instructions include that dependency.

Browser screenshot validation was attempted but Chromium downloads failed to produce usable archives in this environment. No claim of browser visual regression acceptance is made. Run `npm install`, `npx playwright install chromium`, start Django, then run `npm run test:browser`; review desktop/mobile screenshots under artifacts/browser. Also exercise authenticated pages with approved test pupils and sandbox merchants.

These checks do not establish live Stripe/PayPal merchant eligibility, Paynow split/refund API capability, executable FX, school bank settlement, actual Microsoft 365 delivery, VPS deployment, SSL renewal or a tested backup restore. Those gates are explicitly listed in DEPLOYMENT.md and README.md. This is a reviewed development source release, not a live-certified payment service.

The source includes 39 application models and their database fields. See DATABASE_SCHEMA.json. Dataset-specific historical invoice/payment migration mappings await the user's data. The assistant endpoint currently provides curated FAQ answers and support escalation, not an external generative model.
