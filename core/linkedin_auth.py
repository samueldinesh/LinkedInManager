import os
import requests
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/linkedin/callback"  # For local testing

AUTHORIZATION_BASE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

SCOPE = ["w_member_social", "r_liteprofile"]  # Permissions for posting and reading profile

class LinkedInAuth:
    def __init__(self):
        self.oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)

    def get_authorization_url(self):
        authorization_url, state = self.oauth.authorization_url(AUTHORIZATION_BASE_URL)
        return authorization_url, state

    def fetch_token(self, authorization_response):
        token = self.oauth.fetch_token(TOKEN_URL, authorization_response=authorization_response, client_secret=CLIENT_SECRET)
        return token

    def refresh_token(self, refresh_token):
        token = self.oauth.refresh_token(TOKEN_URL, refresh_token=refresh_token, client_secret=CLIENT_SECRET)
        return token

# Function to save tokens to .env
def save_tokens(access_token, refresh_token=None):
    env_path = ".env"
    with open(env_path, "r") as file:
        lines = file.readlines()
    
    with open(env_path, "w") as file:
        for line in lines:
            if line.startswith("LINKEDIN_ACCESS_TOKEN="):
                file.write(f"LINKEDIN_ACCESS_TOKEN={access_token}\n")
            elif line.startswith("LINKEDIN_REFRESH_TOKEN=") and refresh_token:
                file.write(f"LINKEDIN_REFRESH_TOKEN={refresh_token}\n")
            else:
                file.write(line)