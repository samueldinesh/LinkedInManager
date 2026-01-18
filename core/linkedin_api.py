import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")

class LinkedInAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token or ACCESS_TOKEN
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    def get_profile_info(self):
        """Get basic profile information to verify token"""
        url = f"{self.base_url}/people/~"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else None

    def create_text_post(self, text: str) -> dict:
        """Create a text-only post on LinkedIn"""
        url = f"{self.base_url}/ugcPosts"
        
        # First, get the author URN
        author_urn = self._get_author_urn()
        if not author_urn:
            return {"error": "Could not retrieve author URN"}
        
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=self.headers, data=json.dumps(payload))
        
        if response.status_code == 201:
            return {"success": True, "post_id": response.headers.get("x-restli-id")}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}

    def _get_author_urn(self) -> str:
        """Get the author's URN for posting"""
        profile = self.get_profile_info()
        if profile and "id" in profile:
            return f"urn:li:person:{profile['id']}"
        return None

    def create_post_with_media(self, text: str, media_url: str = None) -> dict:
        """Create a post with media (placeholder for future implementation)"""
        # For now, just create text post
        # Media upload requires additional steps
        return self.create_text_post(text)

# Function to post content and update database
async def post_to_linkedin(post_id: int):
    from core.database import async_session
    from core.models import Post
    from sqlalchemy import select, update
    
    async with async_session() as session:
        post = await session.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
        if not post or post.status != "approved":
            return {"error": "Post not found or not approved"}
        
        linkedin_api = LinkedInAPI()
        result = linkedin_api.create_text_post(post.content)
        
        if result.get("success"):
            await session.execute(
                update(Post).where(Post.id == post_id).values(
                    status="posted",
                    posted_at=datetime.utcnow(),
                    linkedin_post_id=result.get("post_id")
                )
            )
        else:
            # Handle error, maybe mark as failed
            pass
        
        await session.commit()
        return result