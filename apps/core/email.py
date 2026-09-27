"""Microsoft 365 SMTP with app-only OAuth2; no basic-auth password fallback."""

import base64
import smtplib
import ssl

import msal
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend


class OAuthSMTPBackend(EmailBackend):
    """Authenticate the configured sender through Exchange SMTP.SendAsApp."""

    def open(self) -> bool:
        """Open TLS and authenticate XOAUTH2; raise on missing tenant permissions."""
        if self.connection:
            return False
        app = msal.ConfidentialClientApplication(
            settings.MS_CLIENT_ID,
            authority="https://login.microsoftonline.com/" + settings.MS_TENANT_ID,
            client_credential=settings.MS_CLIENT_SECRET,
        )
        result = app.acquire_token_for_client(scopes=["https://outlook.office365.com/.default"])
        if "access_token" not in result:
            raise RuntimeError("Microsoft OAuth token acquisition failed.")
        connection = smtplib.SMTP(
            settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=settings.EMAIL_TIMEOUT
        )
        try:
            connection.ehlo()
            connection.starttls(context=ssl.create_default_context())
            connection.ehlo()
            payload = (
                f'user={settings.EMAIL_HOST_USER}\x01auth=Bearer {result["access_token"]}\x01\x01'
            )
            status, _ = connection.docmd(
                "AUTH", "XOAUTH2 " + base64.b64encode(payload.encode()).decode()
            )
            if status != 235:
                raise smtplib.SMTPAuthenticationError(status, b"OAuth SMTP authentication rejected")
        except Exception:
            connection.close()
            raise
        self.connection = connection
        return True
