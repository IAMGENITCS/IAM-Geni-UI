import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]
API_BASE = "http://127.0.0.1:8000"
REDIRECT_URI = "http://localhost:8501"
LOGO_PATH = "tcs_logo.png"