import os
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials
from google_auth_oauthlib.flow import Flow
from google.cloud import firestore
import json

# Initialize Firebase Admin
if not firebase_admin._apps:
    try:
        # If service account json exists, use it, else default to application default credentials
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "app/service_account.json")
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
        print("Firebase Admin initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Firebase Admin: {e}")

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify Firebase Auth token for API protection.
    Bypassed for testing.
    """
    return {"uid": "mock_user123", "email": "mock@example.com", "name": "Mock User"}

class AdwordsOAuthService:
    def __init__(self):
        # We assume the user creates a standard Desktop/Web OAuth client ID and puts the secret json in root or .env
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/admin/settings")
        self.scopes = ["https://www.googleapis.com/auth/adwords"]
        self.use_mock = os.getenv("USE_MOCK_AUTH", "False").lower() == "true"
        self.db = firestore.Client() if not self.use_mock else None

    def get_authorization_url(self):
        if not self.client_id or not self.client_secret:
            raise HTTPException(status_code=500, detail="Missing Google OAuth credentials in environment.")
            
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url

    def exchange_code_for_token(self, code: str):
        if self.use_mock:
            return {"status": "success", "message": "Mock auth successful."}
            
        if not self.client_id or not self.client_secret:
            raise HTTPException(status_code=500, detail="Missing Google OAuth credentials in environment.")
            
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Save the refresh token to Firestore
            self._save_refresh_token(credentials.refresh_token)
            
            return {
                "status": "success", 
                "message": "Successfully connected to Google Ads"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to exchange token: {e}")
            
    def _save_refresh_token(self, refresh_token):
        if not refresh_token:
            return
            
        # Store in a configuration collection
        doc_ref = self.db.collection('system_config').document('adwords_auth')
        doc_ref.set({
            'refresh_token': refresh_token,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
