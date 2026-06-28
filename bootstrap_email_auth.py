"""One-off: run Gmail OAuth to create token.json (bypasses the bootstrap catch-22)."""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "./email/credentials.json")
token_path = os.getenv("GMAIL_TOKEN_PATH", "./email/token.json")

print(f"Using credentials: {creds_path}")
print(f"Will write token to: {token_path}")
print("Opening browser for Google authorization...")

flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
creds = flow.run_local_server(port=8080)

with open(token_path, "w") as f:
    f.write(creds.to_json())

print(f"SUCCESS: token written to {token_path}")
