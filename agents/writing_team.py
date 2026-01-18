import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import List

from core.database import async_session
from core.models import Post, Trend
from core.rate_limiter import RateLimiter
from core.llm_caller import call_llm
from sqlalchemy import select, update

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WritingTeam:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    async def _call_llm_with_rate_limit(self, prompt: str) -> str:
        """Call LLM using intelligent API pool (Gemma first, then Gemini)"""
        async with self.rate_limiter:
            # Uses API pool: tries Gemma (14.4K RPD) first, then Gemini (20 RPD)
            response = await call_llm(prompt)
            return response

    async def generate_post_content(self, post_id: int):
        logger.info(f"Generating content for post ID {post_id}...")
        
        async with async_session() as session:
            result = await session.execute(select(Post).where(Post.id == post_id))
            post = result.scalar_one_or_none()
            if not post:
                logger.error(f"Post with ID {post_id} not found.")
                return
            
            # Get related trend if available
            trend_info = ""
            if post.trend_id:
                trend_result = await session.execute(select(Trend).where(Trend.id == post.trend_id))
                trend = trend_result.scalar_one_or_none()
                if trend:
                    trend_info = f"Related Trend: {trend.title} - {trend.description}"
            
            # Determine the type of content based on category
            if post.category == "lesson":
                content = await self._generate_lesson(post.title, post.content, trend_info)
            elif post.category == "breakthrough":
                content = await self._generate_breakthrough(post.title, post.content, trend_info)
            elif post.category == "scheme":
                content = await self._generate_scheme(post.title, post.content, trend_info)
            else:
                content = await self._generate_general(post.title, post.content, trend_info)
            
            # Edit and format for LinkedIn
            edited_content = await self._edit_content(content)
            linkedin_formatted = await self._format_for_linkedin(edited_content)
            
            # Update the post in database
            await session.execute(
                update(Post).where(Post.id == post_id).values(content=linkedin_formatted, status="approved")
            )
            await session.commit()
        
        logger.info(f"Content generated for post '{post.title}'")

    async def _generate_lesson(self, title: str, description: str, trend_info: str) -> str:
        prompt = f"""
        Write an educational LinkedIn post about Quantum Computing as a lesson.
        
        Title: {title}
        Description: {description}
        {trend_info}
        
        The post should:
        - Be engaging and educational
        - Explain a concept clearly
        - Include practical applications
        - End with a question to encourage engagement
        - Keep it under 2000 characters
        """
        return await self._call_llm_with_rate_limit(prompt)

    async def _generate_breakthrough(self, title: str, description: str, trend_info: str) -> str:
        prompt = f"""
        Write a LinkedIn post announcing a breakthrough in Quantum Computing.
        
        Title: {title}
        Description: {description}
        {trend_info}
        
        The post should:
        - Express excitement about the development
        - Explain the significance
        - Mention implications for the field
        - Encourage discussion
        - Keep it under 2000 characters
        """
        return await self._call_llm_with_rate_limit(prompt)

    async def _generate_scheme(self, title: str, description: str, trend_info: str) -> str:
        prompt = f"""
        Write a LinkedIn post about a government scheme or opportunity in Quantum Computing.
        
        Title: {title}
        Description: {description}
        {trend_info}
        
        The post should:
        - Highlight the opportunity
        - Explain eligibility and benefits
        - Encourage applications
        - Include relevant links if available
        - Keep it under 2000 characters
        """
        return await self._call_llm_with_rate_limit(prompt)

    async def _generate_general(self, title: str, description: str, trend_info: str) -> str:
        prompt = f"""
        Write a general LinkedIn post about Quantum Computing.
        
        Title: {title}
        Description: {description}
        {trend_info}
        
        Make it engaging and relevant to the Quantum community.
        Keep it under 2000 characters.
        """
        return await self._call_llm_with_rate_limit(prompt)

    async def _edit_content(self, content: str) -> str:
        prompt = f"""
        Edit the following LinkedIn post for clarity, engagement, and professionalism:
        
        {content}
        
        Ensure it's concise, error-free, and optimized for LinkedIn audience.
        """
        return await self._call_llm_with_rate_limit(prompt)

    async def _format_for_linkedin(self, content: str) -> str:
        prompt = f"""
        Format the following content for LinkedIn posting:
        
        {content}
        
        Add appropriate emojis, line breaks, and hashtags related to Quantum Computing, AI, IoT, Bioinformatics.
        Ensure it's ready to copy-paste into LinkedIn.
        """
        return await self._call_llm_with_rate_limit(prompt)

    async def generate_all_draft_posts(self):
        logger.info("Generating content for all draft posts...")
        
        async with async_session() as session:
            result = await session.execute(select(Post).where(Post.status == "draft"))
            draft_posts = result.scalars().all()
        
        for post in draft_posts:
            await self.generate_post_content(post.id)
            await asyncio.sleep(1)  # Small delay between generations

# Example of how to run the writing team
async def run_writing_team():
    rate_limiter = RateLimiter(calls=15, period=60)
    team = WritingTeam(rate_limiter)
    await team.generate_all_draft_posts()
    logger.info("Writing team completed generating content.")

if __name__ == "__main__":
    asyncio.run(run_writing_team())