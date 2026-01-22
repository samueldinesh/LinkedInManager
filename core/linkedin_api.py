import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class LinkedInAPI:
    def __init__(self, access_token=None):
        # Get token at runtime (not import time) so we pick up newly saved tokens
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    def get_profile_info(self):
        """Get basic profile information to verify token"""
        import logging
        logger = logging.getLogger(__name__)
        
        # With openid scope, we can use the /userinfo endpoint
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.get(url, headers=headers)
        
        logger.info(f"LinkedIn userinfo API response: {response.status_code}")
        if response.status_code == 200:
            user_info = response.json()
            logger.info(f"User info: {user_info}")
            return user_info
        else:
            logger.error(f"LinkedIn API error: {response.text}")
            return None

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
        import logging
        logger = logging.getLogger(__name__)
        
        profile = self.get_profile_info()
        if profile and "sub" in profile:
            # The 'sub' field from userinfo contains the member ID
            member_id = profile['sub']
            urn = f"urn:li:person:{member_id}"
            logger.info(f"Author URN: {urn}")
            return urn
        
        logger.error("Could not extract member ID from profile")
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
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
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