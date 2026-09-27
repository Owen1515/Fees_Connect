# Microsoft 365 OAuth2 SMTP

The mailbox `support@feesconnect.com` does not yet exist. A Microsoft 365 administrator must provision it and the FeesConnect domain before enabling production email. The application uses this mailbox as sender and Reply-To for support, verification, password resets and receipts.

## Administrator setup

1. Verify feesconnect.com in Microsoft 365 and configure its mail DNS. Create/license the support mailbox as required by your tenant. Configure SPF, DKIM and DMARC before delivery acceptance testing.
2. Register a single-tenant application in Microsoft Entra. Record tenant ID and application/client ID. Create a protected client credential with a rotation date.
3. In Office 365 Exchange Online application permissions, configure SMTP.SendAsApp and obtain administrator consent. This is not Microsoft Graph Mail.Send.
4. Register the application's service principal in Exchange Online using New-ServicePrincipal. Its ObjectId is the Enterprise Application service-principal object ID, not the app-registration object ID.
5. Grant the application access to the sender mailbox following Microsoft's SMTP client-credentials instructions. Restrict the permitted mailbox. Where your tenant uses Application RBAC, scope Application SMTP.SendAsApp to support@feesconnect.com and avoid also granting an unnecessarily broad application permission.
6. Confirm SMTP AUTH is permitted for this mailbox with OAuth2 under tenant policies. An app password does not replace OAuth2.
7. Set MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET and EMAIL_HOST_USER. DEFAULT_FROM_EMAIL must identify the permitted sender.

The backend requests `https://outlook.office365.com/.default`, connects to `smtp.office365.com:587`, upgrades with STARTTLS and authenticates using XOAUTH2. It has no password fallback and does not log access tokens.

## Verify delivery

Use production settings and a running worker. Create a verified test-recipient account, then run:

```bash
python manage.py send_test_email recipient@example.com
```

This queues a message; success means its OutboxMessage becomes sent and the recipient actually receives it. Check Exchange message trace for failures. Test verification links, password reset links, plain-text alternatives and PDF receipts. Never confuse console output in development with Microsoft delivery.

All HTTP-triggered mail goes through the database outbox and Celery. Retries back off and eventually enter dead_letter. SMTP acceptance plus a process crash may cause a duplicate email on retry; exact-once SMTP delivery is not guaranteed. Payment allocation remains idempotent independently of email delivery.

Official setup references:
- https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth
- https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/smtp-app-rbac-onboarding
