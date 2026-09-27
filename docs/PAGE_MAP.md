# Step 3: complete page and URL mapping

All uploaded HTML files are retained under reference/frontend/ for comparison. Converted templates live under templates/feesconnect/. Canonical routes are namespaced; old `*.html` paths redirect to the matching route. Legacy Node token fragments cannot safely be converted into new Django tokens; reset.html/verify.html request fresh email links.

| Uploaded HTML | Django view | Canonical route / name |
| --- | --- | --- |
| index.html | core TemplateView | `/` / core:home |
| home.html | RedirectView | `/home.html` → core:home |
| auth.html | RedirectView | `/auth.html` → accounts:login |
| login.html | accounts.views.login | `/accounts/login/` / accounts:login |
| register.html | accounts.views.register | `/accounts/register/` / accounts:register |
| forgot-password.html | accounts.views.request_token | `/accounts/password/reset/` / accounts:reset_request |
| resend-verification.html | accounts.views.request_token | `/accounts/verification/resend/` / accounts:resend |
| reset.html | accounts.views.reset_confirm | `/accounts/password/reset/<token>/` / accounts:reset_confirm |
| verify.html | accounts.views.verify | `/accounts/verify/<token>/` / accounts:verify |
| account.html | dashboard.views.home | `/account/` / dashboard:home |
| privacy.html | core TemplateView | `/privacy/` / core:privacy |
| demo.html | core TemplateView | `/demo/` / core:demo |

The demo preserves its overview, payment wizard, activity, school directory, help, about, receipt and welcome screens under client-side hash navigation. They remain explicitly labelled sample data and do not call live payment services. Their real equivalents use Django invoice, checkout, history, receipt, account and support routes.

## Added pages

| Page | URL name |
| --- | --- |
| Checkout and quote review | payments:checkout |
| Success / failed / pending | payments:status chooses template from trusted state |
| Poll payment status | payments:status_json |
| Receipt HTML / PDF | payments:receipt / payments:receipt_pdf |
| Invoice list / HTML / PDF | fees:list / fees:invoice / fees:invoice_pdf |
| Invoice creation | fees:issue_invoice |
| Transaction history / CSV | payments:history / payments:export |
| Refund request | payments:refund |
| Reconciliation report | payments:reconciliation |
| Student registration/guardian claim | fees:student_register |
| School onboarding / administration | fees:school_register / fees:school_workspace |
| TOTP setup / verify / recovery display | accounts:otp_setup / accounts:otp_verify; recovery follows successful setup |
| Verification sent / confirmed | accounts:verification_sent / accounts:verification_confirmed |
| Password reset sent / complete | accounts:reset_sent / accounts:reset_complete |
| Profile / password change | accounts:profile / accounts:password_change |
| Support / ticket | support:home / support:ticket |
| Terms / contact | core:terms / core:contact |
| Styled errors | config.urls handler403 / handler404 / handler500 |

Health endpoints are core:healthz and core:readyz. API routes are api:chat, api:payments and api:invoices. All unsafe browser forms require CSRF. Login/register remain public; financial resources re-check authorisation on every request.
