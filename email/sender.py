"""
Email sender - sends cold emails via Gmail API
"""
import os
import base64
import logging
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.auth.oauthlib.flow import InstalledAppFlow
    from google.api_core import retry
    import googleapiclient.discovery
except ImportError:
    print("Warning: Google API libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client")

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class EmailSender:
    """Send emails via Gmail API."""
    
    def __init__(self, credentials_path: str = "./email/credentials.json"):
        self.credentials_path = credentials_path
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        try:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Credentials file not found: {self.credentials_path}")
                logger.info("Please download credentials from Google Cloud Console and place at: " + self.credentials_path)
                return
            
            # Load credentials
            creds = None
            token_path = "./email/token.json"
            
            if os.path.exists(token_path):
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=8080)
                
                # Save token for reuse
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = googleapiclient.discovery.build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API authenticated successfully")
        
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
    
    def send_email(self, to_email: str, subject: str, body: str, 
                  resume_path: str = None, cover_letter_path: str = None) -> bool:
        """
        Send email with optional attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            resume_path: Path to resume PDF/DOCX to attach
            cover_letter_path: Path to cover letter to attach
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.service:
                logger.error("Gmail service not authenticated")
                return False
            
            # Create message
            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = subject
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Attach resume
            if resume_path and os.path.exists(resume_path):
                self._attach_file(message, resume_path)
            
            # Attach cover letter
            if cover_letter_path and os.path.exists(cover_letter_path):
                self._attach_file(message, cover_letter_path)
            
            # Send message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {'raw': raw_message}
            
            result = self.service.users().messages().send(userId='me', body=send_message).execute()
            
            logger.info(f"Email sent successfully to {to_email} (message id: {result['id']})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _attach_file(self, message: MIMEMultipart, file_path: str):
        """Attach file to email message."""
        try:
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(file_path)}'
            )
            message.attach(part)
            logger.debug(f"Attached file: {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to attach file {file_path}: {e}")
    
    def compose_email(self, template_path: str, replacements: Dict[str, str]) -> str:
        """
        Compose email from template with placeholder replacements.
        
        Args:
            template_path: Path to email template
            replacements: Dictionary of {{key}} -> value replacements
        
        Returns:
            Composed email body
        """
        try:
            with open(template_path, 'r') as f:
                body = f.read()
            
            for key, value in replacements.items():
                body = body.replace(f"{{{{{key}}}}}", str(value))
            
            return body
        
        except Exception as e:
            logger.error(f"Failed to compose email from {template_path}: {e}")
            return ""


# Example usage
if __name__ == "__main__":
    sender = EmailSender()
    
    # Test email (requires Gmail authentication first)
    test_email = {
        "to": "test@example.com",
        "subject": "Test Email from Applyr",
        "body": "This is a test email",
        "resume_path": "./resume/master_resume.pdf"
    }
    
    # Uncomment to test
    # sender.send_email(**test_email)
