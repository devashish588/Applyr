"""
Gmail OAuth Service — Secure Gmail API integration
===================================================

OAuth flow:
  1. GET /api/gmail/auth-url       → returns Google auth URL
  2. User authorizes in browser    → Google redirects to callback
  3. GET /api/gmail/callback?code= → exchanges code for token, stores securely
  4. GET /api/gmail/status         → returns connection state (never exposes tokens)

Token refresh happens automatically on send if token is expired.
Tokens are stored in GMAIL_TOKEN_PATH (./email/token.json) — never exposed in logs/API.
"""

import base64
import json
import logging
import os
import time
from datetime import datetime, timezone
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
ROOT = Path(__file__).resolve().parents[2]

# State store for OAuth flow (in-memory, single-user dev server)
_oauth_sessions: Dict[str, Tuple[str, float]] = {}
_OAUTH_SESSION_TTL_SECONDS = 600


def _resolve_project_path(path: str) -> str:
    p = Path(path)
    return str(p if p.is_absolute() else ROOT / p)


def _prune_oauth_sessions() -> None:
    now = time.time()
    for state, (_, created_at) in list(_oauth_sessions.items()):
        if now - created_at > _OAUTH_SESSION_TTL_SECONDS:
            _oauth_sessions.pop(state, None)


class GmailService:
    """Handles Gmail OAuth, token management, and email sending."""

    def __init__(self):
        self.credentials_path = _resolve_project_path(
            os.getenv("GMAIL_CREDENTIALS_PATH", "./email_module/credentials.json")
        )
        self.token_path = _resolve_project_path(
            os.getenv("GMAIL_TOKEN_PATH", "./email_module/token.json")
        )
        self._service = None
        self._creds = None

    # ------------------------------------------------------------------ #
    # Status / Validation
    # ------------------------------------------------------------------ #

    @property
    def has_credentials_file(self) -> bool:
        return os.path.exists(self.credentials_path)

    @property
    def has_token(self) -> bool:
        return os.path.exists(self.token_path)

    def get_status(self) -> dict:
        """Return connection status — never exposes tokens."""
        status = "not_configured"
        account = None
        token_valid = False
        token_expired = False
        expires_at = None

        if not self.has_credentials_file:
            status = "missing_credentials"
        elif not self.has_token:
            status = "not_authenticated"
        else:
            creds = self._load_token()
            if creds is None:
                status = "invalid_token"
            else:
                token_valid = creds.valid
                if hasattr(creds, "expiry") and creds.expiry:
                    expires_at = creds.expiry.isoformat() if creds.expiry else None
                    if creds.expiry.tzinfo is None:
                        expiry_utc = creds.expiry.replace(tzinfo=timezone.utc)
                    else:
                        expiry_utc = creds.expiry
                    token_expired = expiry_utc < datetime.now(timezone.utc)

                # Try to extract account email from token
                if hasattr(creds, "id_token") and creds.id_token:
                    try:
                        payload = json.loads(
                            base64.urlsafe_b64decode(
                                creds.id_token.split(".")[1] + "=="
                            )
                        )
                        account = payload.get("email")
                    except Exception:
                        pass

                if token_valid and not token_expired:
                    status = "connected"
                elif token_expired:
                    # Try auto-refresh
                    if self._refresh_token():
                        status = "connected"
                        token_expired = False
                    else:
                        status = "expired_token"
                else:
                    status = "unauthorized"

        return {
            "status": status,
            "configured": self.has_credentials_file and self.has_token,
            "account": account or os.getenv("FROM_EMAIL"),
            "has_credentials": self.has_credentials_file,
            "has_token": self.has_token,
            "token_valid": token_valid,
            "token_expired": token_expired,
            "expires_at": expires_at,
        }

    def is_ready(self) -> bool:
        """Check if Gmail is fully ready to send."""
        s = self.get_status()
        return s["status"] == "connected"

    # ------------------------------------------------------------------ #
    # OAuth Flow
    # ------------------------------------------------------------------ #

    def get_auth_url(self, redirect_uri: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate Google OAuth URL with explicit PKCE. Returns (url, error)."""
        try:
            from google_auth_oauthlib.flow import Flow
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                pkce="S256",
                autogenerate_code_verifier=False,
            )
            auth_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
            code_verifier = getattr(flow.oauth2session, "_code_verifier", None)
            if not code_verifier:
                return None, "Failed to generate OAuth PKCE verifier"
            _prune_oauth_sessions()
            _oauth_sessions[state] = (code_verifier, time.time())
            logger.info("[gmail] OAuth URL generated (PKCE enabled)")
            return auth_url, None
        except Exception as e:
            logger.error("[gmail] Failed to generate auth URL: %s", e)
            return None, str(e)

    def handle_callback(self, code: str, state: str, redirect_uri: str) -> Tuple[bool, str]:
        """Handle OAuth callback — exchange code for token, store securely. Returns (success, message)."""
        try:
            _prune_oauth_sessions()
            session = _oauth_sessions.pop(state, None)
            if not session:
                logger.warning("[gmail] State mismatch or expired session in OAuth callback")
                return False, "OAuth session expired. Please try connecting Gmail again."
            
            code_verifier, _ = session

            from google_auth_oauthlib.flow import Flow
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                pkce="S256",
                autogenerate_code_verifier=False,
            )
            
            flow.oauth2session._code_verifier = code_verifier
            flow.fetch_token(code=code)
                
            creds = flow.credentials

            # Store token securely
            os.makedirs(os.path.dirname(self.token_path) or ".", exist_ok=True)
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())

            self._creds = creds

            account = "Unknown"
            if hasattr(creds, "id_token") and creds.id_token:
                try:
                    payload = json.loads(
                        base64.urlsafe_b64decode(
                            creds.id_token.split(".")[1] + "=="
                        )
                    )
                    account = payload.get("email", "Unknown")
                except Exception:
                    pass

            logger.info("[gmail] OAuth callback successful — account: %s", account)
            return True, f"Gmail connected as {account}"
        except Exception as e:
            logger.error("[gmail] OAuth callback failed: %s", e)
            return False, str(e)

    # ------------------------------------------------------------------ #
    # Token Management
    # ------------------------------------------------------------------ #

    def _load_token(self):
        """Load credentials from token file."""
        try:
            from google.oauth2.credentials import Credentials
            if not os.path.exists(self.token_path):
                return None
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            self._creds = creds
            return creds
        except Exception as e:
            logger.error("[gmail] Failed to load token: %s", e)
            return None

    def _refresh_token(self) -> bool:
        """Auto-refresh expired token. Returns True if successful."""
        try:
            from google.auth.transport.requests import Request
            creds = self._load_token()
            if not creds:
                return False
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.token_path, "w") as f:
                    f.write(creds.to_json())
                self._creds = creds
                logger.info("[gmail] Token refreshed successfully")
                return True
            if creds and creds.valid:
                return True
            return False
        except Exception as e:
            logger.error("[gmail] Token refresh failed: %s", e)
            return False

    def revoke_token(self) -> bool:
        """Revoke Gmail access. Returns True if successful."""
        try:
            from google.auth.transport.requests import Request
            creds = self._load_token()
            if creds:
                creds.revoke(Request())
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
            self._creds = None
            self._service = None
            logger.info("[gmail] Token revoked")
            return True
        except Exception as e:
            logger.warning("[gmail] Token revoke failed: %s", e)
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
            return False

    # ------------------------------------------------------------------ #
    # Gmail API Service
    # ------------------------------------------------------------------ #

    def _ensure_service(self):
        """Build Gmail API service with token refresh on expiry."""
        try:
            from google.auth.transport.requests import Request
            import googleapiclient.discovery

            creds = self._load_token()
            if not creds:
                return False

            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(self.token_path, "w") as f:
                        f.write(creds.to_json())
                    self._creds = creds
                else:
                    return False

            self._service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)
            return True
        except Exception as e:
            logger.error("[gmail] Failed to build Gmail service: %s", e)
            return False

    # ------------------------------------------------------------------ #
    # Sending
    # ------------------------------------------------------------------ #

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[list] = None,
        from_email: Optional[str] = None,
    ) -> dict:
        """Send email via Gmail API. Returns result dict."""
        try:
            if not self._service:
                if not self._ensure_service():
                    return {"success": False, "error": "Gmail not configured or token expired"}

            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            if from_email:
                message["from"] = from_email
            message.attach(MIMEText(body, "plain"))

            for path in (attachments or []):
                if path and os.path.exists(path):
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{os.path.basename(path)}"',
                    )
                    message.attach(part)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = (
                self._service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )

            msg_id = result.get("id", "unknown")
            logger.info("[gmail] Sent to %s: %s", to, msg_id)
            return {"success": True, "message_id": msg_id, "to": to}
        except Exception as e:
            logger.error("[gmail] Send failed: %s", e)
            return {"success": False, "error": str(e)}

    def send_test(self, to: Optional[str] = None) -> dict:
        """Send a test email to verify Gmail is working."""
        recipient = to or os.getenv("FROM_EMAIL") or "test@example.com"
        result = self.send_email(
            to=recipient,
            subject="Applyr — Gmail Test",
            body=(
                "This is a test email from Applyr AI Agent.\n\n"
                "Your Gmail integration is working correctly.\n\n"
                f"Sent at: {datetime.now().isoformat()}\n"
                "— Applyr"
            ),
        )
        return {
            **result,
            "to": recipient,
            "provider": "gmail",
            "timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------ #
    # Quota / Usage
    # ------------------------------------------------------------------ #

    def get_quota(self) -> dict:
        """Get Gmail API quota information."""
        try:
            if not self._service:
                if not self._ensure_service():
                    return {"error": "Gmail not configured"}
            # Gmail API doesn't have a direct quota endpoint for free tier
            # We estimate based on send history
            return {
                "provider": "gmail",
                "daily_limit": "Unknown (Gmail API free tier)",
                "usage": None,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_account_email(self) -> Optional[str]:
        """Get the connected Gmail account email address."""
        try:
            if not self._service:
                if not self._ensure_service():
                    return None
            profile = self._service.users().getProfile(userId="me").execute()
            return profile.get("emailAddress")
        except Exception:
            return os.getenv("FROM_EMAIL")


# ------------------------------------------------------------------ #
# Singleton
# ------------------------------------------------------------------ #

_gmail_instance: Optional[GmailService] = None


def get_gmail_service() -> GmailService:
    global _gmail_instance
    if _gmail_instance is None:
        _gmail_instance = GmailService()
    return _gmail_instance
