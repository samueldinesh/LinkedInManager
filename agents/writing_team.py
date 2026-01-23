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
            response = await call_llm(prompt)
            return response

    async def generate_post_content(self, post_id: int):
        """Generate high-quality LinkedIn post with a single optimized prompt."""
        logger.info(f"Generating content for post ID {post_id}...")
        
        async with async_session() as session:
            result = await session.execute(select(Post).where(Post.id == post_id))
            post = result.scalar_one_or_none()
            if not post:
                logger.error(f"Post with ID {post_id} not found.")
                return
            
            # Get related trend if available
            trend_info = ""
            topic_area = "technology"
            if post.trend_id:
                trend_result = await session.execute(select(Trend).where(Trend.id == post.trend_id))
                trend = trend_result.scalar_one_or_none()
                if trend:
                    trend_info = f"Related Trend: {trend.title} - {trend.description}"
                    # Extract topic area from trend category or title
                    if "quantum" in trend.title.lower():
                        topic_area = "Quantum Computing"
                    elif "ai" in trend.title.lower() or "artificial" in trend.title.lower():
                        topic_area = "Artificial Intelligence"
                    elif "iot" in trend.title.lower():
                        topic_area = "Internet of Things"
                    elif "bio" in trend.title.lower():
                        topic_area = "Bioinformatics"
                    else:
                        topic_area = "Deep Tech"
            
            # Generate content with single high-quality prompt
            linkedin_content = await self._generate_linkedin_post(
                title=post.title,
                description=post.content,
                category=post.category,
                trend_info=trend_info,
                topic_area=topic_area
            )
            
            # Update the post in database
            await session.execute(
                update(Post).where(Post.id == post_id).values(content=linkedin_content, status="approved")
            )
            await session.commit()
        
        logger.info(f"Content generated for post '{post.title}'")

    async def _generate_linkedin_post(
        self, 
        title: str, 
        description: str, 
        category: str, 
        trend_info: str,
        topic_area: str
    ) -> str:
        """
        Generate a complete, ready-to-post LinkedIn post in a SINGLE LLM call.
        
        This consolidates the previous 3-step process (generate → edit → format)
        into one high-quality prompt.
        """
        
        # Category-specific guidance
        category_guidance = {
            "lesson": """
                - Frame this as an educational explainer
                - Use a simple analogy or metaphor to explain the concept
                - Include a "Did you know?" or surprising fact
                - End with "What aspect would you like me to explain next?"
            """,
            "breakthrough": """
                - Lead with the exciting news/development
                - Explain why this matters (impact on industry/society)
                - Express genuine enthusiasm
                - End with "What do you think this means for the future?"
            """,
            "scheme": """
                - Highlight the opportunity clearly
                - Mention eligibility, deadlines, and benefits
                - Use action-oriented language ("Apply now", "Don't miss this")
                - End with "Have you applied? Share your experience!"
            """,
        }
        
        guidance = category_guidance.get(category, """
            - Share an insightful perspective
            - Make it relatable to professionals in the field
            - End with an engaging question
        """)
        
        prompt = f"""You are a LinkedIn content expert writing for a thought leader in {topic_area}.

TASK: Write a viral LinkedIn post that is ready to copy-paste.

TOPIC: {title}
CONTEXT: {description}
{trend_info}

CATEGORY-SPECIFIC GUIDANCE:
{guidance}

STRICT FORMATTING RULES:
1. HOOK (First Line): Bold, attention-grabbing statement. Under 10 words. Use a surprising fact, question, or bold claim.

2. BODY (3-4 Short Paragraphs):
   - Use short sentences and line breaks for readability
   - Include a real-world example or analogy
   - Add 2-3 relevant emojis naturally (🔬💡🚀⚡🧬)
   - NO bullet points - use flowing prose

3. CALL TO ACTION (Last Line): End with an engaging question that invites comments.

4. HASHTAGS: Add exactly 4-5 hashtags at the very end.
   Examples: #QuantumComputing #AI #FutureTech #Innovation #DeepTech

5. LENGTH: Keep the ENTIRE post under 1500 characters.

IMPORTANT: 
- Output ONLY the final post content
- NO explanations, NO markdown formatting, NO quotation marks around the output
- The post should be IMMEDIATELY ready to paste into LinkedIn
"""

        return await self._call_llm_with_rate_limit(prompt)

    async def generate_all_draft_posts(self):
        """Generate content for all draft posts."""
        logger.info("Generating content for all draft posts...")
        
        async with async_session() as session:
            result = await session.execute(select(Post).where(Post.status == "draft"))
            draft_posts = result.scalars().all()
        
        logger.info(f"Found {len(draft_posts)} draft posts to generate.")
        
        for post in draft_posts:
            await self.generate_post_content(post.id)
            await asyncio.sleep(1)  # Small delay between generations
        
        logger.info("All draft posts generated.")

# Example of how to run the writing team
async def run_writing_team():
    rate_limiter = RateLimiter(calls=15, period=60)
    team = WritingTeam(rate_limiter)
    await team.generate_all_draft_posts()
    logger.info("Writing team completed generating content.")

if __name__ == "__main__":
    asyncio.run(run_writing_team())