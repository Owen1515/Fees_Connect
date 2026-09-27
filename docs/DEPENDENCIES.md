# Step 4: tested dependency versions

Python 3.12.14 was used for validation. Django stays on the requested 5.x series (5.2 LTS). All direct/transitive versions are frozen in requirements.lock. PostgreSQL 16 is the production target.

| Package | Version |
| --- | --- |
| Django | 5.2.17 |
| djangorestframework | 3.18.1 |
| django-crispy-forms | 2.7 |
| crispy-bootstrap5 | 2026.9 |
| celery | 5.6.3 |
| redis | 8.1.0 |
| whitenoise | 6.12.0 |
| gunicorn | 26.2.0 |
| django-environ | 0.14.0 |
| psycopg | 3.3.6 |
| stripe | 15.6.1 |
| paynow | 1.0.8 |
| msal | 1.39.0 |
| django-otp | 1.7.3 |
| django-axes | 8.3.1 |
| weasyprint | 70.0 |
| pytest | 9.1.1 |
| pytest-django | 4.14.0 |
| pytest-cov | 7.1.0 |
| factory-boy | See requirements.lock |
| black | 26.5.1 |
| ruff | 0.16.8 |
| isort | 9.0.1 |
| pre-commit | See requirements.lock |
| sentry-sdk | 2.70.0 |

The frontend uses custom FeesConnect CSS. crispy-bootstrap5 generates accessible form markup while django.css scopes the necessary Bootstrap-style form classes; global Bootstrap CSS is not loaded because it would reset the existing template design. WeasyPrint renders the same receipt-content partial as the HTML receipt.

PayPal uses its HTTPS REST API through requests rather than an unofficial Django payment package. Paynow's official SDK payment object is used with explicit HTTP timeouts and separate poll/hash verification because the inspected SDK transport lacks those protections.

Provider/source references:
- https://www.djangoproject.com/download/
- https://docs.stripe.com/connect/direct-charges
- https://docs.stripe.com/connect/direct-charges-fee-payer-behavior
- https://developers.paynow.co.zw/docs/paynow/python_quickstart/
- https://github.com/paynow/Paynow-Python-SDK
- https://developer.paypal.com/sdk/orders/v2/definitions/order_request
- https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth

SECURE_BROWSER_XSS_FILTER is not a functioning Django 5.2 security feature. CSP, escaping, CSRF, HTTPS and content-type hardening provide the actual implemented controls. Scope and package selections follow the user's authorisation to complete all remaining steps without further approval pauses.
