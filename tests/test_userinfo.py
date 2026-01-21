import os
import requests
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
print(f"Token: {access_token[:50]}..." if access_token else "No token found")

# LinkedIn's userinfo endpoint (part of OpenID Connect)
# This should work with the current scopes
url = "https://api.linkedin.com/v2/userinfo"
headers = {
    "Authorization": f"Bearer {access_token}"
}

print(f"\nTesting: {url}")
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
