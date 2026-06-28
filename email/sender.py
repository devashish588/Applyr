"""
Email sender — Dual provider: Resend (primary) + Gmail API (fallback).

Fixes applied:
  1. gmail_configured now checks BOTH credentials.json AND token.json exist
     (previously: credentials.json alone was treated as "configured", even
     with OAuth never completed — this is exactly why the UI said
     "configured" but sends silently failed)
  2. GMAIL_TOKEN_PATH from .env is now actually used everywhere instead of
     a hardcoded "./email/token.json" string scattered through the class
  3. Added provider_status() for a real health check — returns granular
     state (credentials / token / authenticated / can_send) instead of a
     single boolean the UI can't explain
  4. Added gmail_authenticated property that actually validates the token
     is non-expired and refreshable, not just "the file exists"
  5. send_test() now returns the detailed status, not just success:false
"""

import base64
import logging
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailSender:
    """Send emails via Resend API (primary) or Gmail API (fallback)."""

    def __init__(self):
        self.resend_key   = os.getenv("RESEND_API_KEY", "")
        self.from_email   = os.getenv("FROM_EMAIL", "")
        self.from_name    = os.getenv("FROM_NAME", "Applyr AI")

        # FIX 2: GMAIL_TOKEN_PATH from .env actually used now
        self.gmail_credentials = os.getenv("GMAIL_CREDENTIALS_PATH", "./email/credentials.json")
        self.gmail_token_path  = os.getenv("GMAIL_TOKEN_PATH",       "./email/token.json")

        self._gmail_service = None

    # ── Provider readiness checks ────────────────────────────────────────────
    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_key and self.from_email)

    @property
    def gmail_credentials_exist(self) -> bool:
        return os.path.exists(self.gmail_credentials)

    @property
    def gmail_token_exists(self) -> bool:
        return os.path.exists(self.gmail_token_path)

    @property
    def gmail_configured(self) -> bool:
        """
        FIX 1: requires BOTH the OAuth client file AND a completed token.
        credentials.json alone means OAuth was never finished — sends
        would fail at _ensure_gmail_service() with a confusing error,
        or worse, silently try to open a browser on a headless server.
        """
        return self.gmail_credentials_exist and self.gmail_token_exists

    @property
    def gmail_authenticated(self) -> bool:
        """
        Stronger check than gmail_configured — actually loads the token
        and verifies it's valid or refreshable, not just present on disk.
        A token.json can exist but be expired with a dead refresh_token.
        """
        if not self.gmail_configured:
            return False
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(self.gmail_token_path, SCOPES)
            if creds.valid:
                return True
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.gmail_token_path, "w") as f:
                    f.write(creds.to_json())
                return creds.valid
            return False
        except Exception as e:
            logger.warning(f"[email] Gmail token validation failed: {e}")
            return False

    @property
    def configured(self) -> bool:
        return self.resend_configured or self.gmail_configured

    def provider_status(self) -> dict:
        """
        FIX 3: granular health check for the Settings page / dashboard.
        Replaces the old binary "configured: true/false" that hid exactly
        which step (credentials vs token vs auth) was actually missing.
        """
        resend_ready = self.resend_configured
        gmail_creds  = self.gmail_credentials_exist
        gmail_token  = self.gmail_token_exists
        gmail_auth   = self.gmail_authenticated if (gmail_creds and gmail_token) else False

        active_provider = None
        if resend_ready:
            active_provider = "resend"
        elif gmail_auth:
            active_provider = "gmail"

        return {
            "active_provider": active_provider,
            "can_send": bool(active_provider),
            "resend": {
                "configured": resend_ready,
                "from_email": self.from_email or None,
            },
            "gmail": {
                "credentials": gmail_creds,
                "token": gmail_token,
                "authenticated": gmail_auth,
                "credentials_path": self.gmail_credentials,
                "token_path": self.gmail_token_path,
            },
        }

    # ── Sending ───────────────────────────────────────────────────────────────
    def send(self, to: str, subject: str, body: str, attachments: list[str] | None = None) -> bool:
        if not to:
            logger.error("[email] No recipient address — cannot send")
            return False

        if self.resend_configured:
            return self._send_resend(to, subject, body, attachments or [])
        if self.gmail_configured:
            return self._send_gmail(to, subject, body, attachments or [])

        status = self.provider_status()
        logger.error(
            f"[email] No provider ready. Resend configured={status['resend']['configured']}, "
            f"Gmail credentials={status['gmail']['credentials']}, "
            f"Gmail token={status['gmail']['token']}. "
            "Set RESEND_API_KEY, or complete Gmail OAuth (run send_test() once interactively)."
        )
        return False

    def _send_resend(self, to: str, subject: str, body: str, attachments: list[str]) -> bool:
        try:
            import resend
            resend.api_key = self.resend_key

            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to],
                "subject": subject,
                "text": body,
            }

            if attachments:
                from resend import Attachment
                atts = []
                for path in attachments:
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            atts.append(Attachment(
                                filename=os.path.basename(path),
                                content=base64.b64encode(f.read()).decode(),
                            ))
                if atts:
                    params["attachments"] = atts

            response = resend.Emails.send(params)
            logger.info(f"[email] Sent via Resend to {to}: {response.get('id', 'OK')}")
            return True
        except Exception as e:
            logger.error(f"[email] Resend send failed: {e}")
            return False

    def _send_gmail(self, to: str, subject: str, body: str, attachments: list[str]) -> bool:
        try:
            if not self._gmail_service:
                self._ensure_gmail_service()
            if not self._gmail_service:
                logger.error("[email] Gmail service unavailable — auth likely incomplete")
                return False

            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            message.attach(MIMEText(body, "plain"))

            for path in attachments:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
                    message.attach(part)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = self._gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
            logger.info(f"[email] Sent via Gmail to {to}: {result.get('id', 'OK')}")
            return True
        except Exception as e:
            logger.error(f"[email] Gmail send failed: {e}")
            return False

    def _ensure_gmail_service(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            import googleapiclient.discovery

            # FIX 2: use self.gmail_token_path everywhere, not a hardcoded string
            creds = None
            if os.path.exists(self.gmail_token_path):
                creds = Credentials.from_authorized_user_file(self.gmail_token_path, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.gmail_credentials, SCOPES)
                    creds = flow.run_local_server(port=8080)
                with open(self.gmail_token_path, "w") as f:
                    f.write(creds.to_json())
            self._gmail_service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"[email] Gmail auth failed: {e}")

    def send_test(self, to: str | None = None) -> dict:
        """
        Send a test email to verify the provider is working.
        FIX 5: now returns full provider_status() so failures are
        diagnosable from the response alone, not just success:false.
        """
        recipient = to or self.from_email or "test@example.com"
        status_before = self.provider_status()

        success = self.send(
            to=recipient,
            subject="Applyr — Test Email",
            body=(
                "This is a test email from Applyr AI Agent.\n\n"
                "If you are reading this, your email provider is configured correctly.\n\n"
                "— Applyr"
            ),
        )

        return {
            "success": success,
            "to": recipient,
            "provider": status_before["active_provider"],
            "status": status_before,
        }


class GmailSender(EmailSender):
    """Shim for backward compatibility with orchestrator imports."""
    pass