import os
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict

from core.database import async_session
from core.models import Trend, WeeklyPlan, Post
from core.rate_limiter import RateLimiter
from core.llm_caller import call_llm
from sqlalchemy import select

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentStrategyAgent:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    async def _call_llm_with_rate_limit(self, prompt: str) -> str:
        """Call LLM using intelligent API pool (Gemma first, then Gemini)"""
        async with self.rate_limiter:
            # Uses API pool: tries Gemma (High Quota) first
            response = await call_llm(prompt)
            return response

    async def create_weekly_plan(self) -> WeeklyPlan:
        logger.info("Creating weekly content plan...")
        
        # Calculate week start (Monday of current week)
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        
        # Check if plan for this week already exists
        async with async_session() as session:
            existing_plan = await session.execute(
                select(WeeklyPlan).where(WeeklyPlan.week_start == week_start)
            )
            existing = existing_plan.scalar_one_or_none()
            if existing:
                logger.info(f"Plan for week starting {week_start} already exists (ID: {existing.id}). Skipping creation.")
                return existing
        
        # Get recent trends from the database
        async with async_session() as session:
            result = await session.execute(
                select(Trend).order_by(Trend.discovered_at.desc()).limit(20)
            )
            recent_trends = result.scalars().all()
        
        if not recent_trends:
            logger.warning("No trends found in database. Cannot create plan.")
            return None
        
        # Prepare trends data for Gemma
        trends_data = "\n".join([
            f"- {trend.title}: {trend.description} (Category: {trend.category}, Region: {trend.region})"
            for trend in recent_trends
        ])
        
        prompt = f"""
        Based on the following recent trends, create a customized weekly content plan for a LinkedIn page focused on educational content and community building.
        
        The plan should be tailored to the specific topics and regions found in the trends.

        Trends:
        {trends_data}

        Create a plan for the next 7 days with the following structure:
        - 3 Educational Lessons (explain concepts, applications, or fundamentals)
        - 2 Breakthrough Announcements (share exciting new developments)
        - 2 Scheme/Opportunity Alerts (highlight funding, programs, or opportunities, especially in India)

        For each post, provide:
        - Day of the week
        - Category (Lesson, Breakthrough, Scheme)
        - Title
        - Brief description of what the post will cover
        - Which trend(s) it relates to

        Format the response as a JSON-like structure:
        {{
            "posts": [
                {{
                    "day": "Monday",
                    "category": "Lesson",
                    "title": "Title here",
                    "description": "Brief description",
                    "related_trends": ["Trend title 1", "Trend title 2"]
                }},
                ...
            ]
        }}
        """
        
        try:
            response_text = await self._call_llm_with_rate_limit(prompt)
            plan_data = self._parse_llm_response(response_text)
            
            # Create WeeklyPlan and Posts in database
            weekly_plan = await self._save_plan_to_db(plan_data, recent_trends)
            return weekly_plan
        except Exception as e:
            logger.error(f"Error creating weekly plan: {e}")
            return None

    def _parse_llm_response(self, response_text: str) -> Dict:
        # Placeholder for parsing Gemini's JSON-like response
        # In a real scenario, use json.loads or more robust parsing
        logger.info("Parsing Gemini response for weekly plan")
        try:
            import json
            import re
            
            # Clean up the response text first
            cleaned_text = response_text.strip()
            
            # Remove markdown code block markers if present
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1]
            if "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[0]
            
            cleaned_text = cleaned_text.strip()
            
            return json.loads(cleaned_text)
        except Exception as e:
            logger.warning(f"Could not parse Gemini response as JSON: {e}. Returning empty plan.")
            return {"posts": []}

    async def _save_plan_to_db(self, plan_data: Dict, trends: List[Trend]) -> WeeklyPlan:
        logger.info("Saving weekly plan to database...")
        
        # Calculate week start (Monday of current week)
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        
        async with async_session() as session:
            async with session.begin():
                # Create WeeklyPlan
                weekly_plan = WeeklyPlan(
                    week_start=week_start,
                    status="draft"
                )
                session.add(weekly_plan)
                await session.flush()  # Get the ID
                
                # Create Posts
                for post_data in plan_data.get("posts", []):
                    # Find related trend IDs
                    related_trend_titles = post_data.get("related_trends", [])
                    related_trend_ids = []
                    for trend in trends:
                        if trend.title in related_trend_titles:
                            related_trend_ids.append(trend.id)
                    
                    post = Post(
                        plan_id=weekly_plan.id,
                        trend_id=related_trend_ids[0] if related_trend_ids else None,
                        title=post_data["title"],
                        content=post_data["description"],  # Placeholder, will be expanded later
                        category=post_data["category"].lower(),
                        status="draft"
                    )
                    session.add(post)
                
                await session.commit()
        
        logger.info(f"Weekly plan saved with {len(plan_data.get('posts', []))} posts.")
        return weekly_plan

# Example of how to run the agent
async def run_content_strategy():
    rate_limiter = RateLimiter(calls=15, period=60)
    agent = ContentStrategyAgent(rate_limiter)
    plan = await agent.create_weekly_plan()
    if plan:
        logger.info(f"Created plan for week starting {plan.week_start}")
    else:
        logger.info("No plan created.")

if __name__ == "__main__":
    asyncio.run(run_content_strategy())