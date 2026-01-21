import os
import requests
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
print(f"Token: {access_token[:50]}..." if access_token else "No token found")

# Test the LinkedIn /me endpoint
url = "https://api.linkedin.com/v2/me"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0"
}

print(f"\nTesting: {url}")
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
