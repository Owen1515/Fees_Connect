# FeesConnect Django project brief and model specification

Status: Step 1 reviewed; Step 2 model proposal prepared from the user's seven answers, awaiting confirmation. No application code has been written. Later decisions below supersede conflicting wording in the original requirements summary. The original archive inventory is preserved.

## Scope and staged approvals

Build the Django backend for FeesConnect at feesconnect.com using the supplied FeesConnect frontend. Work applies only to FeesConnect. The original archive and the Travold and AltraSure applications are not modified by this planning document. Shared files are reference inputs only; FeesConnect must become independently deployable.

Proceed in this order and obtain user confirmation after each step:

1. Inventory uploaded files; propose folders and Django apps.
2. Specify every model, field, relationship, constraint and index.
3. Map every uploaded HTML file and JavaScript-rendered screen to its intended Django view and URL; identify every required new page.
4. Confirm dependency versions and Microsoft 365 email authentication, checking current official documentation and provider capabilities.
5. Implement app by app with comments, docstrings, type hints and tests.

## Required implementation

### Stack and structure

Use Python 3.12+, the latest supported stable patch within the requested Django 5.x series, Django REST Framework, PostgreSQL 16 in production, and SQLite only for local development. Confirm exact versions in Step 4. Introduce the custom User model before initial migrations. Use Django Forms/ModelForms, crispy-forms and Bootstrap with template-specific styling. Use Celery/Redis, WhiteNoise, Gunicorn/Nginx, django-environ or python-decouple, pytest/pytest-django, factory-boy, Black, Ruff, isort, pre-commit and Sentry. Deploy to Ubuntu 22.04+.

Split settings into base/dev/prod. Use services for business logic and gateway integrations; views coordinate forms, authorisation and responses. Retain uploaded HTML filenames where useful, extract shared templates and reference uploaded assets with Django static tags.

### Accounts and security

Email-based custom user with optional phone and parent/student/school_admin/super_admin roles. Implement registration, login, POST logout, email verification, password reset, profile and password changes, TOTP 2FA, Groups/custom permissions and school-scoped access checks. Registration must not grant administrative privileges. Include authentication rate limits, strong password validation, optional HaveIBeenPwned checks and auditable authentication/payment events.

Production hardening requested: secure session and CSRF cookies, one-year HSTS, HTTPS redirect, DENY framing, content-type protection and the browser XSS-filter setting named in the original request. Step 4 must identify unsupported or obsolete settings and document supported equivalents rather than treating a no-op setting as protection. Include styled 403/404/500 pages, CSRF protection, safe output escaping, secret management and structured logging without sensitive credentials or payment data.

### Frontend

Inspect and account for every FeesConnect HTML page, including redirect aliases and the demo. Preserve the supplied logo, colours, typography, responsive layout, inputs, buttons and error treatments. Existing CSS is custom, not Bootstrap: use scoped Bootstrap form styling and crispy template overrides, with visual regression checks before accepting changes.

Required complete experiences include checkout, success, failure, pending USSD confirmation, receipt/invoice HTML and PDF, transaction history, 2FA setup/verification/recovery, verification sent/confirmed, password reset request/sent/confirm/complete, profile/settings, error pages, Terms, Privacy and Contact. Reuse the current account workflows and JavaScript-rendered demo designs where appropriate. Keep demonstration data and state isolated from actual payment and school records. Use AJAX/HTMX for suitable interactions, payment-status polling and chatbot messages.

### Payments

Stripe: official SDK; Checkout or Payment Intents; GBP/USD/EUR; requested card, SEPA, Apple Pay and Google Pay methods subject to verified account/currency eligibility. Store Stripe customer and provider payment-method identifiers only, with explicit recurring-payment consent. Use idempotency on creation calls and verified webhook signatures. Handle payment_intent.succeeded, payment_intent.payment_failed and charge.refunded, together with additional events required by the chosen Checkout flow.

Paynow: official SDK; hosted redirect and supported mobile push flows. Requested channels are EcoCash, OneMoney, Telecash, Vpayments, ZIPIT and bank transfer; requested currencies are USD and ZWL. Confirm currently available channels and local currency support in Step 4 and with the merchant configuration before implementation. Validate hashes on status updates, reconcile with trusted provider data, poll outstanding payments every five minutes with Celery beat and offer a pending-page status endpoint. Provide a finance reconciliation report.

Unified layer: Payment records contain payer, fee, amount, currency, gateway, status, reference, gateway reference, metadata and timestamps. Step 2 will define related ledger, allocation, refund and event records. Use an abstract gateway interface, replay-safe webhook processing, transactional state transitions, explicit retry handling and amount/currency/reference checks. Preserve the existing distinction between provider confirmation, settlement and school allocation. Generate PDF receipts from the receipt template using WeasyPrint or ReportLab and send asynchronously. Provide audited refund workflows, using provider APIs where supported; confirm Paynow refund capabilities rather than inventing an endpoint.

### Email

Microsoft 365 SMTP at smtp.office365.com:587 with TLS; sender and credentials come from environment variables. Document EMAIL_HOST_USER, EMAIL_HOST_PASSWORD and DEFAULT_FROM_EMAIL plus OAuth2/MSAL configuration where applicable. Step 4 will verify current tenant authentication requirements; do not assume app passwords bypass disabled basic authentication. All transactional messages use Celery, branded HTML and plain-text alternatives.

Email types: welcome, verification, password reset, successful payment with PDF receipt, failed payment, pending payment, processed refund, receipt/invoice; support transcripts and administrator payment notifications are optional. Provide python manage.py send_test_email and deployment verification instructions.

### Data, support and testing

Commit migrations. Define indexes for payer, status, created timestamp and reference, plus appropriate constraints. Use PostgreSQL JSONB for gateway metadata. Include daily pg_dump backup and retention documentation with restoration instructions.

Provide authenticated DRF /api/support/chat/ integration with the user's existing chatbot service, configurable credentials and timeouts. Preserve support tickets and connect the widget. Confirm the upstream API contract; optional conversation persistence must be explicit.

Use pytest/pytest-django and factory-boy, with measured coverage of at least 85%. Test authentication, forms, permissions and cross-school access, payment creation, mocked webhooks, replay safety, Paynow hash validation, mocked email, all wired template views and critical state transitions. Mocked tests do not substitute for Stripe/Paynow sandbox and real Microsoft 365 delivery checks.

### Deployment and maintainability

Deliver a fully documented .env.example, dependency configuration, pre-commit setup, README, deployment checklist, Postman/Insomnia collection, Nginx config, Gunicorn/Celery worker/Celery beat systemd services, database backups and optional Docker/Compose alternative.

Document Namecheap DNS, feesconnect.com and www.feesconnect.com TLS via Certbot, dedicated PostgreSQL credentials, Redis, secrets outside version control, static collection to /var/www/feesconnect/static/, UFW allowing 22/80/443, SSH Fail2ban, Sentry and uptime monitoring. Include /healthz/, deployment and rollback procedures, database-compatible release transitions and worker restarts. Confirm deployment mechanics before claiming zero downtime.

Follow the user's requirement for explanatory comments throughout every authored code line, clear function/class/method docstrings describing purpose/arguments/returns/errors, type hints, field help_text or comments, commented settings and documented views/services. Explain generated or third-party code separately. Do not claim a system is bulletproof or production-verified without evidence. Document test results and unresolved external configuration.

## Step 1 findings

- The outer archive contains 241 file entries. The direct feesconnect/ subtree contains 27 files: 12 HTML, 6 JavaScript, 2 CSS, 2 image/icon assets, robots.txt, README.md, package.json and 2 Node server modules.
- The embedded FeesConnect_V4_Independent.zip has 53 file entries. Its 27 FeesConnect files are byte-for-byte identical to the outer FeesConnect files; they are a packaged duplicate, not another frontend version.
- index.html is the landing page. account.html combines linked-pupil checkout, payment records, support tickets, automated guidance, profile and password changes.
- auth.html redirects to login.html; home.html redirects to index.html. These aliases must remain accounted for in Step 3.
- demo.html is a JavaScript shell. app.js renders overview, payment flow, activity, school directory, help, about, receipt and welcome screens. These screens are not separate uploaded HTML files.
- Authentication has login, register, forgot-password, resend-verification, reset and verify HTML files. privacy.html also exists. The remaining required standalone pages need a Step 3 gap mapping.
- The existing Node backend implements accounts and Paynow-related flows. It depends on shared integration/http.cjs and integration/payment-security.cjs. Existing tests, school configuration and operations scripts are migration references.
- The approved palette is emerald #0DA35A, lime #9ACB47, evergreen #063D2E and action green #087343. Font stack starts with Inter and falls back to system fonts. The supplied logo is PNG; favicon.svg embeds raster artwork.
- No actual pupil or school operational dataset appears in the FeesConnect subtree. config/schools.example.json contains disabled placeholder merchant settings. Migration needs remain a user question.

## Proposed folders

All paths below are relative to a new independent feesconnect-django/ project. This is a proposed structure, not generated application code.

| Path | Purpose |
| --- | --- |
| manage.py | Django command entrypoint |
| config/settings/base.py, dev.py, prod.py | Shared and environment-specific settings |
| config/urls.py, wsgi.py, asgi.py, celery.py | Routing and application/task entrypoints |
| apps/accounts/ | Identity, verification, 2FA, permissions and profiles |
| apps/fees/ | Schools, enrolments, payer links, fee schedules, invoices and allocation rules |
| apps/payments/ | Payment lifecycle, gateway adapters, webhooks, refunds, receipts and reconciliation |
| apps/dashboard/ | Role-specific dashboards, activity and finance reports |
| apps/support/ | Support tickets, chatbot proxy and optional conversations |
| apps/core/ | Public/legal pages, shared email service, audit utilities and health checks |
| apps/api/ | DRF routing, serializers and thin authenticated API endpoints |
| apps/*/migrations/, services/, tests/ | Versioned schema, business operations and app tests as applicable |
| apps/payments/services/gateways/ | Abstract interface and Stripe/Paynow adapters |
| templates/base.html, includes/, layouts/ | Shared shell, header/footer/navigation and public/auth/workspace layouts |
| templates/feesconnect/ | Converted uploaded HTML preserving source filenames |
| templates/accounts/, fees/, payments/, dashboard/, support/, core/ | New application pages and partials |
| templates/emails/, errors/, crispy/ | HTML/plain-text email, error and form-rendering templates |
| static/feesconnect/ | Supplied CSS/JS and assets, maintaining relative organisation |
| tests/ | Integration, permissions, webhook replay, template and visual checks |
| docs/ | Page mapping, architecture, provider configuration and runbooks |
| deployment/nginx/, systemd/, scripts/ | VPS services, proxy, backups and release/rollback scripts |
| deployment/docker/ | Optional Dockerfile and Compose configuration |
| postman/ | API collection with placeholders, no secrets |
| pyproject.toml, requirements/, .pre-commit-config.yaml | Pinned dependencies and code-quality configuration |
| .env.example, .gitignore, README.md, PROJECT_BRIEF.md | Configuration contract and maintainer documentation |

Production-generated receipts, logs and backups belong in protected runtime storage, outside public static assets and outside version control. School boundaries must be enforced in queries and permissions even if separate databases or schemas are not selected.

## Confirmed business decisions from the user's Step 1 response

1. Full or partial fee payments only. The payer bears transaction charges. Scheduled instalment plans, automatic recurring debits, discounts and late penalties are not included in this release.
2. Students can register their school details, sign in/out, pay, see payment history and view/download invoices and receipts. A user can manage pupils across several schools and hold multiple roles.
3. Schools require manual approval. The requested funds flow sends school principal directly to each school's merchant account and the FeesConnect share directly to the platform account. The total customer transaction charge is 3%, intended to cover bank/network/gateway costs and leave a platform margin.
4. Local currencies are USD and ZiG, replacing the original ZWL request. International payments require currency conversion. Requested methods include PayPal, Visa, Mastercard, EcoCash, bank transfer and virtual cards, alongside compatible methods in the original brief.
5. Microsoft 365 OAuth2 is mandatory. Email accounts are intended for support. Exact support address and transactional From/Reply-To addresses remain to be supplied.
6. Existing data must be migrated. A sample, format, row counts and opening-balance cutover date are still needed.
7. No existing chatbot API exists. Build one stable authenticated Django/DRF support endpoint, with a replaceable internal assistant provider and reliable support-ticket fallback.

## Step 2: business and accounting interpretation

### Payment amount and 3% charge

Proposed interpretation, for user confirmation: the charge is 3% of the school-fee principal actually paid on each transaction, added once. For school principal P, customer charge C = round(P x 0.03), and same-currency customer total T = P + C. A USD 100 partial payment costs USD 103 and reduces the pupil's fee balance by USD 100. There is no extra 3% gateway charge on top.

The school principal target is P. Actual network, processor and FX costs are expenses, not platform revenue. C minus those costs is a transaction contribution margin; it is not net profit after all business overheads, tax, refunds and disputes. Record expected costs at checkout and actual costs from reconciliation. A negative margin must remain visible. Never silently increase the customer charge or deduct a shortfall from school principal.

The fixed 3% policy is a business target, not evidence of available provider pricing. Step 4 must establish merchant eligibility, contract pricing, fee incidence, split capability and FX execution. A route without the required settlement capability remains disabled. No fallback to platform custody or a second customer debit without a new agreed design. Provider-held balances and later bank payouts are distinct from immediate receipt in a bank account.

Stripe's direct-charge configuration determines whether its processing costs are billed to the school or platform. PayPal platform fees require enabled marketplace/platform capability and seller onboarding. The Paynow documentation reviewed establishes merchant settlement and selectable fee incidence, but does not establish an automatic two-beneficiary split for this proposed integration. Written provider confirmation is still required for that route.

### Currency conversion

Use separate invoice/settlement currency and payer currency. Initially, school settlement currency must equal the invoice currency; a USD invoice is not automatically treated as a ZiG invoice. Use the label ZiG with an internal ZWG currency record and provider-specific mappings verified during integration. Do not relabel historical ZWL amounts as ZiG or merge balances across currencies.

An FX quote defines its direction explicitly: payer-currency units per one invoice-currency unit. Store executable provider quote ID, rate, expiry and rounded payable amount. The quote must be executable through the chosen provider or contracted FX partner. An informational market rate is not authority to promise conversion or school proceeds. Requote expired amounts and obtain renewed payer confirmation before starting a new charge. Issuer conversion of a card bill is separate from a FeesConnect-executed quote.

Clarify whether the 3% must also cover all FX costs, who bears a cost shortfall, and charge refundability before activating a route. No FX surcharge is assumed here. Visa/Mastercard are card networks, EcoCash is a mobile wallet, and virtual cards use the card integration where accepted; they are not all separate gateways. Add a PayPal adapter to the originally requested Stripe/Paynow architecture.

### Roles, school boundaries and approval

Use multiple RoleAssignment records instead of an authoritative single role field on User. A role points to a Django Group permission bundle. A school-admin assignment is always school-scoped; global parent/student capability still requires a verified StudentAccess record for each pupil. super_admin is explicitly granted by authorised platform staff. Django is_staff is admin-site access, not permission to read every school's records. Ordinary school administrators are not Django superusers.

Student self-registration creates a pending school-specific pupil record or a pending claim to an existing pupil. Knowing an admission number never grants access. School staff verify the association before invoices, receipts and history become visible. A guardian's approved access can cover several pupils and schools. A user can have both self-student and guardian links. No new school or user can approve its own privileged access.

School admins can manage their school's pupils, links and billing. Refund approval and merchant configuration are separate restricted permissions; changing school bank routing requires re-verification. Role revocation and pupil-link revocation take effect on the next authorised request. The frontend's chosen role is only a presentation preference.

### Proposed checkout boundary

One checkout targets one invoice, one pupil and one school. A user may pay several schools through separate checkouts. This avoids promising unsupported cross-school splits. A partial payment reduces only the selected invoice principal; it does not create a contractual instalment schedule. Refunds and overpayment corrections remain supported.

## Step 2: complete proposed application-model inventory

This specification proposes 39 application models. These are design declarations, not Django model code. Field types and named relationships below are the intended contract. Final package-owned authentication tables will be documented against pinned versions in Step 4.

### Common types, fields and constraints

- Unless stated otherwise, every model has id UUID primary key, created_at and updated_at timezone-aware timestamps. These are included implicitly in every row below. Append-only records do not change their recorded event facts.
- Text fields use explicit bounded lengths in implementation: names 160, codes 64, provider references 255, currency codes 3 and SHA-256 digests 64. Free-form descriptions are TextField. States are constrained TextChoices, not arbitrary input strings. Metadata/snapshots are validated JSONField, which maps to JSONB on PostgreSQL.
- Money uses DecimalField(20,2), never binary float, for the initially supported two-decimal currencies. Currency is a foreign key to Currency unless a field is explicitly an immutable display snapshot. Rates use DecimalField(24,12); rates are positive. Every monetary record has an explicit currency or inherits a single unambiguous currency through its parent.
- FK means many-to-one; O2O means one-to-one; ? means nullable. Referenced financial entities use PROTECT. User accounts linked to financial records are deactivated rather than deleted. Operational author/reviewer FKs can use SET_NULL with an immutable actor snapshot in audit history. Migrations will state deletion behaviour explicitly.
- Primary keys and unique constraints create indexes. Django FK indexes are retained; the indexes below are additional access-pattern indexes. Avoid duplicate indexes. There is no blanket JSONB GIN index without a query requirement.
- Each tenant-owned query is school-scoped. Cross-table school/currency consistency is checked by transaction services and PostgreSQL constraint triggers where required; a row CHECK alone cannot enforce a relationship across tables. Financial race guarantees are tested on PostgreSQL, not inferred from SQLite.
- Amount positivity, date order and allowed state transitions are enforced. Aggregate limits need row locking and transactional services, with deferred database checks for critical financial invariants where appropriate. UUIDs are identifiers, not access controls.

### accounts app: identity and permissions (3 models)

| Model | Fields beyond common fields | Relationships, indexes and constraints |
| --- | --- | --- |
| User | email, password hash, full_name, phone?, email_verified_at?, is_active, is_staff, is_superuser, last_login?, date_joined, preferred_currency? FK, locale, auth_version integer | Email is USERNAME_FIELD; no username. Unique Lower(email) plus stored canonical email. Inherits PermissionsMixin groups and user_permissions M2M. Index (is_active, created_at). No single-role authorisation field. Password changes increment auth_version and revoke sessions. |
| RoleAssignment | user FK, group FK to Django Group, school? FK, status active/revoked, granted_by? User FK, granted_at, revoked_at? | Partial unique (user, group, school) for active school-scoped rows; separate partial unique (user, group) for active global rows because nullable uniqueness alone is insufficient. Index (school, status, user). Services constrain school_admin to a school and super_admin to global scope. |
| AccountToken | user FK, purpose verification/password_reset, token_digest, email_snapshot, expires_at, consumed_at?, revoked_at?, issued_auth_version | Unique token_digest; index (user, purpose, expires_at). Random raw tokens are sent once, never stored. Password-reset use also checks auth_version. Atomic consume once; no tokens in logs. Session and OTP tables are package-owned. |

### fees app: school and billing records (9 models)

| Model | Fields beyond common fields | Relationships, indexes and constraints |
| --- | --- | --- |
| School | code, legal_name, display_name, registration_number?, country_code, address, contact_email, contact_phone?, status pending/approved/rejected/suspended, requested_by FK User, reviewed_by? FK User, reviewed_at?, review_reason, supported_currencies M2M Currency | Unique code; conditional unique (country_code, registration_number) when supplied. Index (status, created_at). Approved school and eligible merchant connection are both required for checkout. Review changes audited. |
| AcademicPeriod | school FK, code, label, starts_on, ends_on, is_active | Unique (school, code); CHECK ends_on >= starts_on. Index (school, is_active). |
| Student | school FK, admission_number, full_name, class_label?, status pending/active/inactive/rejected, submitted_by? FK User, verified_by? FK User, verified_at? | Unique (school, admission_number); index (school, status, class_label). One school-specific enrolment record; pupils do not need an email to receive an invoice. Pending submissions cannot overwrite imported records. |
| StudentAccess | student FK, user FK, relationship self/parent/guardian/sponsor, status pending/approved/rejected/revoked, can_pay, can_view_invoices, can_view_history, requested_at, reviewed_by? User FK, reviewed_at?, verification_reference? | Unique (student, user); partial unique student for approved relationship=self. Index (user, status), (student, status). Student's school supplies tenant scope. History access excludes another payer's private payment instrument, email or support content. |
| FeeCategory | school FK, code, name, description, is_active | Unique (school, code); index (school, is_active). Names remain configurable until user supplies categories. |
| FeeSchedule | school FK, period FK, category FK, code, revision integer, class_label?, amount, currency FK, is_active | Unique (school, code, revision); amount > 0; index (school, period, is_active). Existing invoices retain snapshots when a schedule changes. No discount, late-penalty or instalment-plan fields. |
| Invoice | school FK, student FK, period? FK, number, currency FK, status draft/issued/void, issued_at?, due_on?, total_amount, document_key?, document_sha256?, import_row? O2O, issued_by? User FK | Unique (school, number); index (school, status, due_on), (student, issued_at). total_amount equals line sum on issue and is then immutable. Financial state unpaid/part_paid/paid/overdue is derived from allocations and adjustments, not overwritten by a browser. Imported opening balances can use period=null. |
| InvoiceLine | invoice FK, position integer, category? FK, schedule? FK, description_snapshot, quantity Decimal(12,3), unit_amount, line_amount | Unique (invoice, position); quantity > 0, unit_amount >= 0, line_amount >= 0. Line currency inherits invoice; line_amount rounded from quantity x unit_amount. School matches category/schedule. Issued lines immutable. |
| InvoiceAdjustment | invoice FK, amount_delta signed money, reason, source_key, approved_by FK User, effective_at, document_key? | Unique (invoice, source_key); nonzero amount_delta; index (invoice, effective_at). Append-only billing error/cutover corrections, not a discount engine. Cannot reduce liability below allocations without an explicit credit/refund exception. |

### payments app: payments and evidence (18 models)

| Model | Fields beyond common fields | Relationships, indexes and constraints |
| --- | --- | --- |
| MerchantAccount | owner_kind school/platform, school? FK, gateway stripe/paynow/paypal/bank_partner, environment test/live, external_account_id, settlement_currency FK, jurisdiction, status pending/enabled/restricted/disabled, credential_secret_ref, verified_capabilities JSON, fee_bearer, verified_at?, payout_destination_fingerprint?, capabilities_version | Unique (gateway, environment, external_account_id, settlement_currency). CHECK school required iff owner_kind=school. Index (school, gateway, status). Capabilities bind allowed methods, presentment currencies, settlement route, split and refund support. Store secret-manager references, never API keys or full banking credentials in JSON. |
| GatewayCustomer | user FK, merchant_account FK, external_customer_id | Unique (user, merchant_account) and (merchant_account, external_customer_id). Customer IDs are account-scoped, particularly for direct Stripe charges; no single globally authoritative Stripe ID on User. |
| SavedPaymentMethod | customer FK, external_method_id, kind, brand?, last_four?, expiry_month?, expiry_year?, consented_at, consent_version, revoked_at? | Unique (customer, external_method_id); index (customer, revoked_at). Provider token only, never PAN/CVV. Supports optional payer-selected reuse; no automatic recurring collection is enabled in this release. |
| FeePolicy | version integer, rate_bps integer default 300, calculation_basis principal, rounding_mode, effective_from, effective_until?, fx_cost_treatment pending/included, shortfall_treatment pending/platform_absorbs/disable_route, charge_refund_policy pending/refundable/nonrefundable/conditional, approved_by? User FK, approved_at? | Unique version; CHECK rate_bps=300 for launch and valid date order. Index effective_from. Versions immutable once used. Unresolved cost/refund policy prevents live-route activation. |
| FXQuote | source_currency FK, payer_currency FK, rate, source_amount, payer_amount, provider, provider_quote_id, merchant_account FK, executable boolean, quoted_at, expires_at, rounding_delta, provider_cost_amount?, provider_cost_currency? FK, metadata JSON | Unique (merchant_account, provider, provider_quote_id). Positive rate/amounts; expiry > quote time. Index (expires_at), (source_currency, payer_currency, quoted_at). source_amount includes quoted principal and combined transaction charge. No FXQuote needed for same-currency payment. |
| PaymentQuote | user FK, invoice FK, school_merchant FK, platform_merchant FK, policy FK, fx_quote? O2O, principal_amount, charge_amount, invoice_currency FK, payer_amount, payer_currency FK, expected_provider_cost?, expected_cost_currency? FK, expected_platform_margin?, expected_margin_currency? FK, payment_method, settlement_plan JSON, capabilities_version, expires_at, accepted_at?, request_digest | Index (user, expires_at), (invoice, created_at). Immutable accepted quote. Same-currency payer_amount=principal+charge. charge=round(principal x .03). Stored settlement plan identifies beneficiaries, cost incidence and expected currency per leg; totals are validated per currency. |
| Payment | user FK, invoice FK, quote? O2O, school FK, merchant_account FK, reference, amount, currency FK, principal_amount, principal_currency FK, charge_amount, charge_currency FK, gateway, status created/pending/succeeded/failed/cancelled/partially_refunded/refunded/review, idempotency_key, request_digest, gateway_ref?, metadata JSON, succeeded_at?, review_reason?, import_row? O2O | Unique reference and (user, idempotency_key); conditional unique (merchant_account, gateway_ref) when present. Index (user, created_at), (school, status, created_at), (status, created_at), (invoice, created_at). amount is actual payer total, never principal. All quoted values are immutable snapshots. Legacy imported records can omit quote through a separately checked import-origin rule; online records always require it. |
| PaymentAttempt | payment FK, attempt_number, provider_idempotency_key, provider_reference?, state created/submitting/unknown/pending/succeeded/failed/cancelled, submitted_at?, completed_at?, error_code?, request_digest, safe_response JSON, encrypted_poll_url? | Unique (payment, attempt_number), (merchant-account scope via payment, provider_idempotency_key) enforced by a namespaced globally unique key. Index (state, updated_at). Uncertain network outcomes are polled/reconciled; do not create a second debit. Provider references tied to attempts retain all captures for overpayment review. |
| InvoiceReservation | invoice FK, payment O2O, principal_amount, currency FK, expires_at, status active/consumed/released/expired | Index (invoice, status, expires_at), (status, expires_at); amount > 0. Reserves outstanding balance under invoice row lock. Reservation expiry does not mean provider failure. |
| PaymentAllocation | payment O2O, invoice FK, principal_amount, currency FK, allocated_at, source_key, allocated_by? User FK | Unique source_key; index (invoice, allocated_at). Allocated principal excludes the 3% charge, must match school/currency and verified payment. May be smaller than paid principal if late success creates surplus; remainder is unapplied pending review/refund. |
| AllocationAdjustment | allocation FK, refund? FK, dispute? FK, delta signed money, reason refund/dispute/restoration/correction, source_key, effective_at, approved_by? User FK | Unique source_key; nonzero delta; index (allocation, effective_at). Append-only reductions/restorations in invoice currency. Cumulative allocation cannot be negative or exceed payment principal. Refunding an unallocated surplus does not create a negative allocation. |
| Refund | payment FK, reference, requested_by FK User, approved_by? FK User, principal_amount, principal_currency FK, payer_principal_amount, charge_refund_amount, payer_refund_total, payer_currency FK, status requested/approved/submitting/unknown/pending/succeeded/failed/rejected, reason, idempotency_key, gateway_ref?, provider_cost_amount?, provider_cost_currency? FK, approved_at?, completed_at?, safe_metadata JSON | Unique reference and idempotency_key; conditional unique (payment, gateway_ref). Index (payment, status), (status, created_at). Total payer refund equals payer principal portion plus charge refund. Lock payment and include pending refunds when enforcing cumulative captured-amount and principal limits. FX refund values are explicit; never apply today's rate blindly. |
| WebhookEvent | merchant_account FK, gateway, dedupe_key, external_event_id?, event_type, payload_digest, encrypted_payload_key?, signature_verified_at, payment? FK, processing_status received/processing/processed/retry/dead_letter, attempt_count, next_retry_at?, processed_at?, error_code? | Unique (merchant_account, dedupe_key); index (processing_status, next_retry_at), (payment, created_at). Provider event ID where available, validated payload digest otherwise. Verify raw payload before durable acceptance; no events created from failed signatures. Business effects also idempotent, independent of event dedupe. |
| SettlementEntry | payment FK, refund? FK, dispute? FK, merchant_account FK, beneficiary school/platform/provider, kind school_principal/platform_charge/processor_cost/fx_cost/refund/dispute/adjustment, direction credit/debit, amount, currency FK, provider_transaction_id, provider_line_id, status pending/confirmed/reversed, settled_at?, bank_payout_ref?, evidence_key?, reversal_of? O2O | Unique (merchant_account, provider_transaction_id, provider_line_id); amount > 0; index (payment, beneficiary), (merchant_account, settled_at), (status, created_at). Provider evidence, not a transfer instruction. Record processor-internal credits separately from confirmed bank payout; corrections append reversals, never erase evidence. |
| ReconciliationRun | merchant_account FK, started_at, finished_at?, period_start, period_end, status running/completed/failed, trigger scheduled/manual, initiated_by? User FK, counts JSON, report_key?, error_code? | Index (merchant_account, period_start, period_end), (status, started_at); valid time window. Only one active run per merchant account via conditional unique constraint. Private downloadable report. |
| ReconciliationItem | run FK, payment? FK, settlement_entry? FK, source_reference, issue_type missing_local/missing_provider/amount_mismatch/currency_mismatch/split_mismatch/duplicate/fee_variance/unapplied, expected_amount?, actual_amount?, currency? FK, status open/resolved/accepted_variance, resolution_note?, resolved_by? User FK, resolved_at? | Unique (run, source_reference, issue_type); index (status, created_at), (payment, status). Imported external entries can initially have no local payment. Different-currency comparisons are separate evidence, never subtraction across currencies. |
| Receipt | payment O2O, number, immutable_snapshot JSON, pdf_key?, pdf_sha256?, rendering_status pending/ready/failed, issued_at, template_version, last_error_code? | Unique number; index (rendering_status, created_at). Generated only for confirmed paid amounts. Snapshot separates school principal, combined charge, currency conversion and outstanding balance. A refund is a separate document, not a rewritten original receipt. Access re-checks payer/pupil relationship and masks other payers' personal details. |
| Dispute | payment FK, provider_reference, payer_amount, payer_currency FK, reason, status open/won/lost/closed, opened_at, response_due_at?, resolved_at?, provider_fee?, provider_fee_currency? FK, evidence_key? | Unique (payment, provider_reference); index (status, response_due_at), (payment, opened_at). Allocation adjustment follows established debit/resolution evidence and prevents double reversal with a refund. |

Payments model note: gateway names and method capabilities are separate. Bank transfers become paid only from trusted bank/provider confirmation or a separately authorised, audited finance reconciliation process, never from a customer's uploaded screenshot. Automatic split capability is a requirement to enable an online route.

### core app: currency, audit, delivery and migration (5 models)

| Model | Fields beyond common fields | Relationships, indexes and constraints |
| --- | --- | --- |
| Currency | code Char(3) PRIMARY KEY instead of UUID, display_name, symbol, minor_units integer, is_active | Code is unique. Initial records USD, ZWG, GBP, EUR with two fractional digits; display ZWG as ZiG. Gateway-specific codes live in verified capability mapping. Historical currencies can be inactive without rewriting records. |
| AuditEvent | actor? User FK, actor_snapshot, school? FK, action, target_type, target_id?, correlation_id, occurred_at, redacted_changes JSON, outcome, ip_digest? | Append-only; index (school, occurred_at), (actor, occurred_at), (target_type, target_id), correlation_id. Exclude secrets, raw tokens, passwords, card data and unrestricted full payloads. |
| OutboxMessage | kind email/task, topic, dedupe_key, user? FK, aggregate_type?, aggregate_id?, template_name?, template_version?, encrypted_payload_key, attachment_keys JSON, state pending/processing/sent/retry/dead_letter, attempt_count, next_attempt_at?, locked_until?, sent_at?, provider_message_id?, last_error_code? | Unique dedupe_key; index (state, next_attempt_at). Insert in same DB transaction as the triggering business event; Celery dispatcher retries durable entries. SMTP cannot guarantee exactly-once delivery across a crash after remote acceptance; use stable message IDs and record that limit. Verification links receive short retention in encrypted payload storage. |
| ImportBatch | school? FK, data_kind schools/students/links/invoices/opening_balances/payments, source_filename, source_sha256, source_system, schema_version, effective_cutover_at, submitted_by FK User, approved_by? FK User, status uploaded/validated/rejected/applying/completed/failed, dry_run_report_key?, source_key, totals JSON, applied_at? | Unique (source_system, source_sha256, data_kind, school) with separate null-school unique constraint. Index (school, status, created_at). Protected source files and explicit cutover prevent importing both historical payments and already-netted balances twice. |
| ImportRow | batch FK, row_number integer, external_id?, row_digest, encrypted_source_key, validation_errors JSON, status pending/valid/invalid/applied/skipped, target_type?, target_id?, applied_at? | Unique (batch, row_number), conditional unique (batch, external_id). Index (batch, status), (target_type, target_id). Model-specific natural keys and an import service dedupe across batches; rows retain source-to-target traceability. No migrated plaintext passwords; unsupported hashes trigger a reset. |

### support app: support and the new assistant (4 models)

| Model | Fields beyond common fields | Relationships, indexes and constraints |
| --- | --- | --- |
| SupportTicket | reference, opened_by FK User, school? FK, payment? FK, subject, category, status open/in_progress/waiting/resolved/closed, assigned_to? User FK, resolved_at? | Unique reference; index (opened_by, created_at), (school, status), (assigned_to, status). Payment/school references must be authorised for the requester; support assignment does not automatically grant all school data. |
| TicketMessage | ticket FK, author? User FK, author_kind user/staff/system, body, visibility requester/internal, sent_at | Index (ticket, sent_at). Internal notes never returned to the requester. No attachment scope assumed for initial release. |
| ChatConversation | user FK, school? FK, status open/closed/escalated, ticket? O2O, consent_version?, retention_until, last_activity_at | Index (user, last_activity_at), retention_until. School context is an authorisation filter, not a permission grant. Expired content purged per agreed retention policy. |
| ChatMessage | conversation FK, role user/assistant/system, sequence integer, content, request_key?, status pending/completed/failed, provider?, model_name?, upstream_request_id?, token_usage JSON, redacted_error_code? | Unique (conversation, sequence); conditional unique (conversation, request_key, role). Index (conversation, created_at). Stable POST /api/support/chat/ accepts a client request ID, and retries reuse the prior result. Store no hidden chain-of-thought. |

### dashboard and api apps

No additional business-data tables. Dashboard selectors read school-scoped billing/payment records; caches are derived and rebuildable. API serializers/views call the same permission checks and services as HTML views. This avoids separate API and webpage versions of a balance.

### Framework and authentication package models

Django Group, Permission, ContentType, Session and admin LogEntry are framework tables, not custom business models. RoleAssignment references Group and Group owns its Permission M2M. The selected OTP package owns TOTP devices, replay counters, throttle state and one-use recovery-token records; secrets must be encrypted at rest and administrative roles must complete 2FA. Exact package table/field names and migrations will be listed in Step 4 after the requested version selection. Do not invent or duplicate a package schema now. Celery beat uses a code-defined schedule unless a database scheduler is explicitly chosen.

## Step 2: critical invariants and workflow rules

1. Pending school approval, pending student claims and missing merchant capability block live payments. Student registration itself does not give school-admin permissions or reveal an existing pupil record.
2. Cross-school object lookup, invoice access, receipt download and export always enforce role plus pupil/school scope. Merely being a parent or student is insufficient.
3. Fee balance = issued invoice principal + approved signed invoice adjustments - successful principal allocations - signed allocation adjustments. A negative allocation adjustment therefore restores unpaid principal. Paid principal and customer charges are never conflated.
4. Under an invoice lock, pending reservations plus allocations cannot exceed current liability. Use PostgreSQL row locks for competing parent/student checkouts. A late external success is recorded as received even if its reservation expired; any excess stays unapplied for reconciliation/refund rather than being hidden or applied twice.
5. Reusing an idempotency key with different parameters returns a conflict. A timeout produces unknown/pending state and provider lookup; no blind re-charge. Multiple provider captures are retained as evidence and routed for review.
6. Only trusted provider/bank evidence can change a payment to succeeded. Browser redirects, chatbot replies and uploaded payment screenshots cannot. Out-of-order notifications cannot downgrade a succeeded payment to failed; refunds and disputes have their own evidence-backed transitions.
7. Lock the Payment when approving refunds. Pending plus successful refunds cannot exceed captured payer funds or remaining school principal. Refund allocations and charge refunds are separately recorded. Until the charge-refund policy is confirmed, live refunds requiring that decision are not automatically executed.
8. Payment confirmation, allocation, processor settlement, FeesConnect fee credit and school bank payout are distinct facts. An absent split leg is a reconciliation exception. SettlementEntry is an evidence register, not a complete corporate general ledger or a stored-value wallet.
9. Immutable quotes, invoice/receipt snapshots, policy versions and gateway configuration versions reproduce the original calculation. Actual provider fees supersede estimates for margin reports without altering customer-agreed totals. Margin reports do not sum different currencies without an explicit reporting FX basis.
10. School funds never pass through a FeesConnect wallet in this proposal. Merchant routing remains disabled until the provider can execute the agreed direct settlement and platform fee arrangement in the relevant jurisdictions.
11. Imports first produce a dry-run report. Validate duplicates, school boundaries, currency, historical payment states and opening-balance treatment before committing a batch. Each imported row is traceable and retries do not duplicate records.
12. The support assistant initially answers curated FeesConnect FAQs and may retrieve only authorised account facts. An internal provider adapter can later add an external model. Unavailable model providers fall back to deterministic answers and ticket escalation. The assistant cannot initiate payments, approve schools, issue refunds or change bank destinations.

## Outstanding decisions for Step 2 confirmation

- Confirm the proposed charge basis: USD 100 principal means USD 103 total. Must 3% include FX costs as well? If actual costs exceed it, should FeesConnect absorb the shortfall or should that payment route be unavailable? How are customer charges handled on refunds?
- In which country is FeesConnect's merchant entity registered, and which Stripe/PayPal/Paynow accounts or marketplace approvals already exist? Zimbabwe is not on Stripe's ordinary supported payments-country list; eligibility must be resolved, not assumed from a diaspora payer's country.
- Supply the support email address and confirm whether that same mailbox should send verification, password resets and receipts using OAuth2, or whether there will be a separate transactional sender.
- Supply a redacted sample of existing data, its format, approximate volume and desired cutover date. School fee category names can be seeded from that data.

These details can remain configuration decisions while Step 3 page mapping proceeds after the user approves this model design. No code or live integration is authorised by this document alone beyond the staged workflow.

## Provider documentation consulted for this proposal

Checked 23 September 2026; recheck implementation-specific API details in Step 4.

- Stripe direct charges: https://docs.stripe.com/connect/direct-charges
- Stripe direct-charge fee incidence: https://docs.stripe.com/connect/direct-charges-fee-payer-behavior
- Stripe country availability: https://stripe.com/global
- PayPal platform-fee capability: https://developer.paypal.com/sdk/orders/v2/definitions/order_request
- PayPal seller PARTNER_FEE onboarding: https://developer.paypal.com/platforms/checkout/standard/customize/auth-capture/
- Paynow merchant settlement and fee incidence: https://www.paynow.co.zw/home/merchanttutorial
- Paynow integration settings: https://developers.paynow.co.zw/docs/paynow/integration_generation/
- Paynow express payment methods: https://developers.paynow.co.zw/docs/paynow/express_checkout_transactions/
- Paynow BillPay ZWG/USD reference (not evidence of capabilities of a different Paynow product): https://developers.paynow.co.zw/docs/billpay/vendor/intro/

Optional suggestions in the user's pasted brief (JWT/mobile API, separate-schema tenancy, extra languages, analytics charts, admin webhook replay and development Compose) are not automatically selected. Agree their scope before implementing them.

## Inventory conventions

The next section lists every outer-archive entry exactly. Listing other products is an inventory operation, not permission to inspect or alter their implementations. The FeesConnect-only embedded deployment inventory follows separately. Other embedded product archives are outside this task's scope and are not expanded.


## Complete outer-archive file inventory (241 entries)

| Archive path | Bytes |
| --- | ---: |
| `travold-platforms-v4/.dockerignore` | 37 |
| `travold-platforms-v4/.env.example` | 869 |
| `travold-platforms-v4/.gitignore` | 57 |
| `travold-platforms-v4/ALTRASURE-BUSINESS-BASELINE.json` | 3228 |
| `travold-platforms-v4/BRAND-ALTRASURE.md` | 1435 |
| `travold-platforms-v4/BRAND-FEESCONNECT.md` | 1456 |
| `travold-platforms-v4/CHANGES-V2.md` | 3229 |
| `travold-platforms-v4/CHANGES-V3.md` | 2711 |
| `travold-platforms-v4/CHANGES-V4.md` | 3137 |
| `travold-platforms-v4/DEPLOYMENT.md` | 13403 |
| `travold-platforms-v4/MIGRATION-ALTRASURE.md` | 2965 |
| `travold-platforms-v4/MIGRATION-FEESCONNECT.md` | 317 |
| `travold-platforms-v4/START-HERE.md` | 5675 |
| `travold-platforms-v4/START-MAC-LINUX.sh` | 247 |
| `travold-platforms-v4/START-WINDOWS.cmd` | 225 |
| `travold-platforms-v4/VALIDATION.md` | 2710 |
| `travold-platforms-v4/altrasure/.gitignore` | 150 |
| `travold-platforms-v4/altrasure/.openai/hosting.json` | 32 |
| `travold-platforms-v4/altrasure/AI-INNOVATION-REVIEW.md` | 10021 |
| `travold-platforms-v4/altrasure/AltraSurev8.html` | 7465452 |
| `travold-platforms-v4/altrasure/BROWSER-RESULTS-v8.json` | 1359 |
| `travold-platforms-v4/altrasure/MANIFEST.json` | 16409 |
| `travold-platforms-v4/altrasure/README-v3.md` | 7587 |
| `travold-platforms-v4/altrasure/README-v4.md` | 11985 |
| `travold-platforms-v4/altrasure/README-v5.md` | 12972 |
| `travold-platforms-v4/altrasure/README-v6.md` | 13315 |
| `travold-platforms-v4/altrasure/README-v7.md` | 18151 |
| `travold-platforms-v4/altrasure/README.md` | 11670 |
| `travold-platforms-v4/altrasure/RELEASE-REVIEW-v4.md` | 10758 |
| `travold-platforms-v4/altrasure/RELEASE-REVIEW-v5.md` | 3499 |
| `travold-platforms-v4/altrasure/RELEASE-REVIEW-v6.md` | 2927 |
| `travold-platforms-v4/altrasure/RELEASE-REVIEW-v7.md` | 3465 |
| `travold-platforms-v4/altrasure/RELEASE-REVIEW-v8.md` | 7059 |
| `travold-platforms-v4/altrasure/RELEASE-REVIEW.md` | 7399 |
| `travold-platforms-v4/altrasure/START-V2.md` | 1026 |
| `travold-platforms-v4/altrasure/TEST-RESULTS.txt` | 18268 |
| `travold-platforms-v4/altrasure/assets/altrasure-logo.png` | 420903 |
| `travold-platforms-v4/altrasure/assets/altrasure-logo.svg` | 561340 |
| `travold-platforms-v4/altrasure/assets/altrasure-supplied-logo.png` | 420903 |
| `travold-platforms-v4/altrasure/assets/altrasure-v5-logo.svg` | 561340 |
| `travold-platforms-v4/altrasure/assets/favicon.svg` | 561339 |
| `travold-platforms-v4/altrasure/auth/auth.js` | 3344 |
| `travold-platforms-v4/altrasure/auth/forgot-password.html` | 2747 |
| `travold-platforms-v4/altrasure/auth/login.html` | 3106 |
| `travold-platforms-v4/altrasure/auth/logout.html` | 488 |
| `travold-platforms-v4/altrasure/auth/logout.js` | 392 |
| `travold-platforms-v4/altrasure/auth/privacy.html` | 2234 |
| `travold-platforms-v4/altrasure/auth/register.html` | 3498 |
| `travold-platforms-v4/altrasure/auth/resend-verification.html` | 2747 |
| `travold-platforms-v4/altrasure/auth/reset.html` | 3020 |
| `travold-platforms-v4/altrasure/auth/site-navigation.js` | 970 |
| `travold-platforms-v4/altrasure/auth/site.css` | 8498 |
| `travold-platforms-v4/altrasure/auth/support.html` | 1405 |
| `travold-platforms-v4/altrasure/auth/support.js` | 1678 |
| `travold-platforms-v4/altrasure/auth/verify.html` | 3012 |
| `travold-platforms-v4/altrasure/build-release.py` | 2444 |
| `travold-platforms-v4/altrasure/dist/index.html` | 7465458 |
| `travold-platforms-v4/altrasure/examples/AltraSure-demo-wording.txt` | 1670 |
| `travold-platforms-v4/altrasure/examples/v7-broker-submission.txt` | 296 |
| `travold-platforms-v4/altrasure/examples/v7-medical-invoice.csv` | 166 |
| `travold-platforms-v4/altrasure/examples/v7-repair-items.csv` | 83 |
| `travold-platforms-v4/altrasure/examples/v7-risk-observations.csv` | 229 |
| `travold-platforms-v4/altrasure/examples/v7-underwriting-guidelines.txt` | 256 |
| `travold-platforms-v4/altrasure/index.html` | 7465942 |
| `travold-platforms-v4/altrasure/package.json` | 210 |
| `travold-platforms-v4/altrasure/register.html` | 248 |
| `travold-platforms-v4/altrasure/server/.env.example` | 602 |
| `travold-platforms-v4/altrasure/server/AltraSurev8.html` | 7465452 |
| `travold-platforms-v4/altrasure/server/README-v4.md` | 18167 |
| `travold-platforms-v4/altrasure/server/README-v5.md` | 4713 |
| `travold-platforms-v4/altrasure/server/README-v6.md` | 5319 |
| `travold-platforms-v4/altrasure/server/README-v7.md` | 8964 |
| `travold-platforms-v4/altrasure/server/README.md` | 11230 |
| `travold-platforms-v4/altrasure/server/bootstrap.cjs` | 926 |
| `travold-platforms-v4/altrasure/server/connected-services.cjs` | 5038 |
| `travold-platforms-v4/altrasure/server/connections.example.json` | 622 |
| `travold-platforms-v4/altrasure/server/engine.cjs` | 230316 |
| `travold-platforms-v4/altrasure/server/package.json` | 308 |
| `travold-platforms-v4/altrasure/server/paynow.cjs` | 1573 |
| `travold-platforms-v4/altrasure/server/paynow.example.json` | 188 |
| `travold-platforms-v4/altrasure/server/projection.cjs` | 2943 |
| `travold-platforms-v4/altrasure/server/security.cjs` | 2838 |
| `travold-platforms-v4/altrasure/server/server.cjs` | 16446 |
| `travold-platforms-v4/altrasure/server/store.cjs` | 1612 |
| `travold-platforms-v4/altrasure/server/tests/connected-services.test.cjs` | 10101 |
| `travold-platforms-v4/altrasure/server/tests/security.test.cjs` | 23066 |
| `travold-platforms-v4/altrasure/server/tests/v5-services.test.cjs` | 7870 |
| `travold-platforms-v4/altrasure/server/tests/v7-services.test.cjs` | 8362 |
| `travold-platforms-v4/altrasure/server/users.example.json` | 1156 |
| `travold-platforms-v4/altrasure/server/v4-routes.cjs` | 12235 |
| `travold-platforms-v4/altrasure/server/v5-routes.cjs` | 4752 |
| `travold-platforms-v4/altrasure/server/v7-routes.cjs` | 6806 |
| `travold-platforms-v4/altrasure/server/v7-services.cjs` | 6781 |
| `travold-platforms-v4/altrasure/server/wording-extract.py` | 792 |
| `travold-platforms-v4/altrasure/server/wording-services.cjs` | 4514 |
| `travold-platforms-v4/altrasure/src/app.css` | 9689 |
| `travold-platforms-v4/altrasure/src/build-research.py` | 17073 |
| `travold-platforms-v4/altrasure/src/build.py` | 4440 |
| `travold-platforms-v4/altrasure/src/core.js` | 36891 |
| `travold-platforms-v4/altrasure/src/landing.css` | 13640 |
| `travold-platforms-v4/altrasure/src/landing.html` | 14081 |
| `travold-platforms-v4/altrasure/src/operations-ui.js` | 34651 |
| `travold-platforms-v4/altrasure/src/operations.js` | 18992 |
| `travold-platforms-v4/altrasure/src/public.js` | 3527 |
| `travold-platforms-v4/altrasure/src/refined.css` | 10706 |
| `travold-platforms-v4/altrasure/src/research.json` | 43482 |
| `travold-platforms-v4/altrasure/src/shell.html` | 3941 |
| `travold-platforms-v4/altrasure/src/theme-v5.json` | 381 |
| `travold-platforms-v4/altrasure/src/ui.js` | 80275 |
| `travold-platforms-v4/altrasure/src/v3-storage.js` | 1275 |
| `travold-platforms-v4/altrasure/src/v3-ui.js` | 40808 |
| `travold-platforms-v4/altrasure/src/v3.css` | 14981 |
| `travold-platforms-v4/altrasure/src/v3.js` | 25265 |
| `travold-platforms-v4/altrasure/src/v4-actuarial.js` | 14208 |
| `travold-platforms-v4/altrasure/src/v4-ui.js` | 53254 |
| `travold-platforms-v4/altrasure/src/v4-zip.js` | 1677 |
| `travold-platforms-v4/altrasure/src/v4.css` | 19915 |
| `travold-platforms-v4/altrasure/src/v4.js` | 47553 |
| `travold-platforms-v4/altrasure/src/v5-extract.js` | 4049 |
| `travold-platforms-v4/altrasure/src/v5-premium.js` | 15103 |
| `travold-platforms-v4/altrasure/src/v5-style-build.py` | 1484 |
| `travold-platforms-v4/altrasure/src/v5-ui.js` | 29848 |
| `travold-platforms-v4/altrasure/src/v5-wordings.js` | 5276 |
| `travold-platforms-v4/altrasure/src/v5.css` | 38746 |
| `travold-platforms-v4/altrasure/src/v5.js` | 12931 |
| `travold-platforms-v4/altrasure/src/v6-roles.js` | 4378 |
| `travold-platforms-v4/altrasure/src/v6-ui.js` | 23813 |
| `travold-platforms-v4/altrasure/src/v6.css` | 5265 |
| `travold-platforms-v4/altrasure/src/v6.js` | 7389 |
| `travold-platforms-v4/altrasure/src/v7-analysis.js` | 5293 |
| `travold-platforms-v4/altrasure/src/v7-ui.js` | 41963 |
| `travold-platforms-v4/altrasure/src/v7.css` | 4556 |
| `travold-platforms-v4/altrasure/src/v7.js` | 21362 |
| `travold-platforms-v4/altrasure/src/v8-ui.js` | 26562 |
| `travold-platforms-v4/altrasure/src/v8.css` | 31770 |
| `travold-platforms-v4/altrasure/src/v8.js` | 15663 |
| `travold-platforms-v4/altrasure/tests/operations.test.cjs` | 8953 |
| `travold-platforms-v4/altrasure/tests/v3-render.test.cjs` | 7432 |
| `travold-platforms-v4/altrasure/tests/v3-workflows.test.cjs` | 12996 |
| `travold-platforms-v4/altrasure/tests/v4-workflows.test.cjs` | 16252 |
| `travold-platforms-v4/altrasure/tests/v5-design.test.cjs` | 3484 |
| `travold-platforms-v4/altrasure/tests/v5-workflows.test.cjs` | 11645 |
| `travold-platforms-v4/altrasure/tests/v6-workflows.test.cjs` | 6324 |
| `travold-platforms-v4/altrasure/tests/v7-workflows.test.cjs` | 13005 |
| `travold-platforms-v4/altrasure/tests/v8-experience.test.cjs` | 9617 |
| `travold-platforms-v4/altrasure/tests/workflows.test.cjs` | 12942 |
| `travold-platforms-v4/altrasure/vendor/JSZIP-LICENSE` | 33753 |
| `travold-platforms-v4/altrasure/vendor/LUCIDE-LICENSE` | 3208 |
| `travold-platforms-v4/altrasure/vendor/PDFJS-LICENSE` | 10174 |
| `travold-platforms-v4/altrasure/vendor/jszip.min.js` | 97630 |
| `travold-platforms-v4/altrasure/vendor/lucide.min.js` | 397450 |
| `travold-platforms-v4/altrasure/vendor/pdf.mjs` | 810118 |
| `travold-platforms-v4/altrasure/vendor/pdf.worker.min.mjs` | 1244253 |
| `travold-platforms-v4/compose.yaml` | 831 |
| `travold-platforms-v4/config/altrasure-workspace.example.json` | 2033 |
| `travold-platforms-v4/config/schools.example.json` | 304 |
| `travold-platforms-v4/config/sites.json` | 123 |
| `travold-platforms-v4/deployment/Caddyfile` | 216 |
| `travold-platforms-v4/deployment/Dockerfile` | 259 |
| `travold-platforms-v4/deployment/container-start.sh` | 134 |
| `travold-platforms-v4/feesconnect/README.md` | 890 |
| `travold-platforms-v4/feesconnect/package.json` | 193 |
| `travold-platforms-v4/feesconnect/public/account.html` | 5091 |
| `travold-platforms-v4/feesconnect/public/account.js` | 5691 |
| `travold-platforms-v4/feesconnect/public/app.js` | 42661 |
| `travold-platforms-v4/feesconnect/public/assets/favicon.svg` | 358512 |
| `travold-platforms-v4/feesconnect/public/assets/feesconnect-logo.png` | 268780 |
| `travold-platforms-v4/feesconnect/public/auth.html` | 217 |
| `travold-platforms-v4/feesconnect/public/auth.js` | 3355 |
| `travold-platforms-v4/feesconnect/public/core.js` | 8867 |
| `travold-platforms-v4/feesconnect/public/demo.html` | 7154 |
| `travold-platforms-v4/feesconnect/public/forgot-password.html` | 2717 |
| `travold-platforms-v4/feesconnect/public/home.html` | 217 |
| `travold-platforms-v4/feesconnect/public/index.html` | 3570 |
| `travold-platforms-v4/feesconnect/public/login.html` | 3078 |
| `travold-platforms-v4/feesconnect/public/payments-ui.js` | 5010 |
| `travold-platforms-v4/feesconnect/public/privacy.html` | 2799 |
| `travold-platforms-v4/feesconnect/public/register.html` | 3454 |
| `travold-platforms-v4/feesconnect/public/resend-verification.html` | 2717 |
| `travold-platforms-v4/feesconnect/public/reset.html` | 2990 |
| `travold-platforms-v4/feesconnect/public/robots.txt` | 204 |
| `travold-platforms-v4/feesconnect/public/site-navigation.js` | 964 |
| `travold-platforms-v4/feesconnect/public/site.css` | 9472 |
| `travold-platforms-v4/feesconnect/public/styles.css` | 27458 |
| `travold-platforms-v4/feesconnect/public/verify.html` | 2982 |
| `travold-platforms-v4/feesconnect/server/payments.cjs` | 9752 |
| `travold-platforms-v4/feesconnect/server/server.cjs` | 17389 |
| `travold-platforms-v4/independent-deployments/AltraSure_V4_Independent.zip` | 17830621 |
| `travold-platforms-v4/independent-deployments/FeesConnect_V4_Independent.zip` | 597119 |
| `travold-platforms-v4/independent-deployments/Travold_V4_Independent.zip` | 1252081 |
| `travold-platforms-v4/index.html` | 320 |
| `travold-platforms-v4/integration/altrasure-gateway.cjs` | 10972 |
| `travold-platforms-v4/integration/http.cjs` | 2126 |
| `travold-platforms-v4/integration/payment-security.cjs` | 2838 |
| `travold-platforms-v4/integration/registration/app.js` | 1333 |
| `travold-platforms-v4/integration/registration/index.html` | 2529 |
| `travold-platforms-v4/integration/registration/style.css` | 8412 |
| `travold-platforms-v4/integration/travold-server.cjs` | 2676 |
| `travold-platforms-v4/package.json` | 651 |
| `travold-platforms-v4/tests/accounts.test.cjs` | 6909 |
| `travold-platforms-v4/tests/altrasure-gateway.test.cjs` | 3538 |
| `travold-platforms-v4/tests/altrasure-migration.test.cjs` | 4876 |
| `travold-platforms-v4/tests/feesconnect-migration.test.cjs` | 4242 |
| `travold-platforms-v4/tests/native-altrasure.test.cjs` | 3965 |
| `travold-platforms-v4/tests/navigation.test.cjs` | 3231 |
| `travold-platforms-v4/tests/package.test.cjs` | 3004 |
| `travold-platforms-v4/tests/payment-ui-loading.test.cjs` | 1116 |
| `travold-platforms-v4/tests/payments.test.cjs` | 5338 |
| `travold-platforms-v4/tools/approve-altrasure.cjs` | 2924 |
| `travold-platforms-v4/tools/bootstrap-altrasure.cjs` | 663 |
| `travold-platforms-v4/tools/build-independent.py` | 9209 |
| `travold-platforms-v4/tools/check-launch.cjs` | 4123 |
| `travold-platforms-v4/tools/configure-domains.py` | 3063 |
| `travold-platforms-v4/tools/feesconnect-operations.cjs` | 872 |
| `travold-platforms-v4/tools/launch.cjs` | 2611 |
| `travold-platforms-v4/tools/migrate-altrasure.cjs` | 3966 |
| `travold-platforms-v4/tools/migrate-feesconnect.cjs` | 593 |
| `travold-platforms-v4/tools/setup.cjs` | 1400 |
| `travold-platforms-v4/tools/start.cjs` | 1163 |
| `travold-platforms-v4/tools/support.cjs` | 1956 |
| `travold-platforms-v4/tools/test-all.cjs` | 515 |
| `travold-platforms-v4/travold/404.html` | 7573 |
| `travold-platforms-v4/travold/README.md` | 468 |
| `travold-platforms-v4/travold/altrasure.html` | 689 |
| `travold-platforms-v4/travold/assets/altrasure-logo.png` | 420903 |
| `travold-platforms-v4/travold/assets/altrasure-logo.svg` | 561340 |
| `travold-platforms-v4/travold/assets/apple-touch-icon.png` | 19691 |
| `travold-platforms-v4/travold/assets/favicon.png` | 3585 |
| `travold-platforms-v4/travold/assets/feesconnect-logo.png` | 268780 |
| `travold-platforms-v4/travold/assets/hero.webp` | 78958 |
| `travold-platforms-v4/travold/assets/travold-logo.jpeg` | 54831 |
| `travold-platforms-v4/travold/easypay.html` | 710 |
| `travold-platforms-v4/travold/feesconnect.html` | 710 |
| `travold-platforms-v4/travold/index.html` | 17461 |
| `travold-platforms-v4/travold/package.json` | 205 |
| `travold-platforms-v4/travold/product-links.js` | 842 |
| `travold-platforms-v4/travold/robots.txt` | 23 |
| `travold-platforms-v4/travold/script.js` | 2708 |
| `travold-platforms-v4/travold/styles.css` | 30670 |
| `travold-platforms-v4/travold/ultrasure.html` | 689 |
| `travold-platforms-v4/FILE-MANIFEST.json` | 24360 |

## Embedded FeesConnect deployment inventory (53 entries)

| Archive path | Bytes |
| --- | ---: |
| `feesconnect-v4/.dockerignore` | 31 |
| `feesconnect-v4/.env.example` | 869 |
| `feesconnect-v4/Caddyfile` | 74 |
| `feesconnect-v4/DEPLOYMENT.md` | 13403 |
| `feesconnect-v4/Dockerfile` | 249 |
| `feesconnect-v4/MIGRATION-ALTRASURE.md` | 2965 |
| `feesconnect-v4/MIGRATION-FEESCONNECT.md` | 317 |
| `feesconnect-v4/README.md` | 1550 |
| `feesconnect-v4/compose.yaml` | 513 |
| `feesconnect-v4/config/altrasure-workspace.example.json` | 2033 |
| `feesconnect-v4/config/schools.example.json` | 304 |
| `feesconnect-v4/config/sites.json` | 123 |
| `feesconnect-v4/feesconnect/README.md` | 890 |
| `feesconnect-v4/feesconnect/package.json` | 193 |
| `feesconnect-v4/feesconnect/public/account.html` | 5091 |
| `feesconnect-v4/feesconnect/public/account.js` | 5691 |
| `feesconnect-v4/feesconnect/public/app.js` | 42661 |
| `feesconnect-v4/feesconnect/public/assets/favicon.svg` | 358512 |
| `feesconnect-v4/feesconnect/public/assets/feesconnect-logo.png` | 268780 |
| `feesconnect-v4/feesconnect/public/auth.html` | 217 |
| `feesconnect-v4/feesconnect/public/auth.js` | 3355 |
| `feesconnect-v4/feesconnect/public/core.js` | 8867 |
| `feesconnect-v4/feesconnect/public/demo.html` | 7154 |
| `feesconnect-v4/feesconnect/public/forgot-password.html` | 2717 |
| `feesconnect-v4/feesconnect/public/home.html` | 217 |
| `feesconnect-v4/feesconnect/public/index.html` | 3570 |
| `feesconnect-v4/feesconnect/public/login.html` | 3078 |
| `feesconnect-v4/feesconnect/public/payments-ui.js` | 5010 |
| `feesconnect-v4/feesconnect/public/privacy.html` | 2799 |
| `feesconnect-v4/feesconnect/public/register.html` | 3454 |
| `feesconnect-v4/feesconnect/public/resend-verification.html` | 2717 |
| `feesconnect-v4/feesconnect/public/reset.html` | 2990 |
| `feesconnect-v4/feesconnect/public/robots.txt` | 204 |
| `feesconnect-v4/feesconnect/public/site-navigation.js` | 964 |
| `feesconnect-v4/feesconnect/public/site.css` | 9472 |
| `feesconnect-v4/feesconnect/public/styles.css` | 27458 |
| `feesconnect-v4/feesconnect/public/verify.html` | 2982 |
| `feesconnect-v4/feesconnect/server/payments.cjs` | 9752 |
| `feesconnect-v4/feesconnect/server/server.cjs` | 17389 |
| `feesconnect-v4/integration/http.cjs` | 2126 |
| `feesconnect-v4/integration/payment-security.cjs` | 2838 |
| `feesconnect-v4/package.json` | 340 |
| `feesconnect-v4/runtime-files.json` | 1649 |
| `feesconnect-v4/tests/accounts.test.cjs` | 6909 |
| `feesconnect-v4/tests/payments.test.cjs` | 5341 |
| `feesconnect-v4/tools/check-service.cjs` | 1591 |
| `feesconnect-v4/tools/configure-domains.py` | 3063 |
| `feesconnect-v4/tools/feesconnect-operations.cjs` | 872 |
| `feesconnect-v4/tools/migrate-altrasure.cjs` | 3966 |
| `feesconnect-v4/tools/migrate-feesconnect.cjs` | 593 |
| `feesconnect-v4/tools/setup.cjs` | 1400 |
| `feesconnect-v4/tools/support.cjs` | 1956 |
| `feesconnect-v4/tools/test-service.cjs` | 520 |
