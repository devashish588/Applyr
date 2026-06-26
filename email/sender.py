"""
Email sender — Dual provider: Resend (primary) + Gmail API (fallback).
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
        self.resend_key = os.getenv("RESEND_API_KEY", "")
        self.from_email = os.getenv("FROM_EMAIL", "")
        self.from_name = os.getenv("FROM_NAME", "Applyr AI")
        self.gmail_credentials = os.getenv("GMAIL_CREDENTIALS_PATH", "./email/credentials.json")
        self._gmail_service = None

    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_key and self.from_email)

    @property
    def gmail_configured(self) -> bool:
        return os.path.exists(self.gmail_credentials)

    @property
    def configured(self) -> bool:
        return self.resend_configured or self.gmail_configured

    def send(self, to: str, subject: str, body: str, attachments: list[str] | None = None) -> bool:
        if self.resend_configured:
            return self._send_resend(to, subject, body, attachments or [])
        if self.gmail_configured:
            return self._send_gmail(to, subject, body, attachments or [])
        logger.error("No email provider configured — set RESEND_API_KEY or configure Gmail credentials")
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
                            import base64
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

            token_path = "./email/token.json"
            creds = None
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.gmail_credentials, SCOPES)
                    creds = flow.run_local_server(port=8080)
                with open(token_path, "w") as f:
                    f.write(creds.to_json())
            self._gmail_service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"[email] Gmail auth failed: {e}")

    def send_test(self, to: str | None = None) -> dict:
        """Send a test email to verify the provider is working."""
        recipient = to or self.from_email or "test@example.com"
        success = self.send(
            to=recipient,
            subject="Applyr — Test Email",
            body=(
                "This is a test email from Applyr AI Agent.\n\n"
                "If you are reading this, your email provider is configured correctly.\n\n"
                "— Applyr"
            ),
        )
        return {"success": success, "to": recipient, "provider": "resend" if self.resend_configured else "gmail"}


class GmailSender(EmailSender):
    """Shim for backward compatibility with orchestrator imports."""
    pass
