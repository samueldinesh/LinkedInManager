import os
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict

from core.database import async_session
from core.database import async_session
from core.models import Trend, WeeklyPlan, Post, ContentTopic
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
                logger.info(f"Plan for week starting {week_start} already exists (ID: {existing.id}). Will append new posts.")
                # Don't return, proceed to generate and append
            else:
                existing = None
        
        # Get recent trends from the database
        async with async_session() as session:
            result = await session.execute(
                select(Trend).order_by(Trend.discovered_at.desc()).limit(20)
            )
            recent_trends = result.scalars().all()
        
        if not recent_trends:
            logger.warning("No trends found in database. Cannot create plan.")
            return None
        
        # ===== CURRICULUM-AWARE TOPIC SELECTION =====
        from core.models import Curriculum
        theme_topic = None
        current_curriculum = None
        
        async with async_session() as session:
            # 1. Check for in_progress curriculum entry
            result = await session.execute(
                select(Curriculum).where(Curriculum.status == "in_progress").limit(1)
            )
            current_curriculum = result.scalar_one_or_none()
            
            if current_curriculum:
                theme_topic = current_curriculum.topic_name
                logger.info(f"Continuing in-progress curriculum: {theme_topic}")
            else:
                # 2. Find highest priority planned entry
                result = await session.execute(
                    select(Curriculum).where(Curriculum.status == "planned").order_by(Curriculum.priority.desc()).limit(1)
                )
                planned = result.scalar_one_or_none()
                
                if planned:
                    theme_topic = planned.topic_name
                    # Update to in_progress
                    planned.status = "in_progress"
                    planned.week_start = datetime.utcnow()
                    await session.commit()
                    current_curriculum = planned
                    logger.info(f"Starting new curriculum: {theme_topic}")
                else:
                    # 3. Fallback: Pick from ContentTopics not yet in Curriculum
                    result = await session.execute(select(ContentTopic).where(ContentTopic.is_active == True))
                    active_topics = result.scalars().all()
                    
                    # Filter out topics already in curriculum
                    existing = await session.execute(select(Curriculum.topic_name))
                    existing_names = {r[0] for r in existing.fetchall()}
                    
                    available = [t for t in active_topics if t.name not in existing_names]
                    
                    if available:
                        import random
                        chosen = random.choice(available)
                        theme_topic = chosen.name
                        # Add to curriculum as in_progress
                        new_curr = Curriculum(
                            topic_name=theme_topic,
                            topic_id=chosen.id,
                            status="in_progress",
                            week_start=datetime.utcnow()
                        )
                        session.add(new_curr)
                        await session.commit()
                        current_curriculum = new_curr
                        logger.info(f"Added new topic to curriculum: {theme_topic}")
                    else:
                        # All topics exhausted, pick random from active
                        import random
                        theme_topic = random.choice(active_topics).name if active_topics else "Emerging Technology"
                        logger.info(f"All topics taught. Recycling: {theme_topic}")


        # Prepare trends data
        trends_data = "\n".join([
            f"- {trend.title}: {trend.description} (Category: {trend.category}, Region: {trend.region})"
            for trend in recent_trends
        ])
        
        prompt = f"""
        Create a weekly content plan for a LinkedIn page focused on educational content.
        
        THEME OF THE WEEK: "{theme_topic}"
        
        Your goal is to create a "Micro-Course" series on this theme, interspersed with breaking news.

        Trends Available (for News posts):
        {trends_data}

        REQUIRED SCHEDULE (7 Days):
        - Monday (Part 1): Introduction to {theme_topic} (Concept & Basics).
        - Tuesday: Breaking News / Trend Analysis (Pick relevant trend).
        - Wednesday (Part 2): How {theme_topic} Works (Deep Dive / Mechanism).
        - Thursday: Breaking News / Opportunity Scheme (Pick relevant trend).
        - Friday (Part 3): Real-world Applications of {theme_topic} (Use Cases).
        - Saturday/Sunday: Recap or Engagement Question.

        Output strictly as JSON:
        {{
            "posts": [
                {{
                    "day": "Monday",
                    "category": "lesson_series",
                    "series_part": 1,
                    "title": "Micro-Course Part 1: [Title]",
                    "description": "Explaining the core concept...",
                    "related_trends": []
                }},
                {{
                    "day": "Tuesday",
                    "category": "news",
                    "title": "[Trend Title]",
                    "description": "Discussing recent news...",
                    "related_trends": ["Trend 1"]
                }}
                ...
            ]
        }}
        """
        
        try:
            response_text = await self._call_llm_with_rate_limit(prompt)
            plan_data = self._parse_llm_response(response_text)
            
            # Create WeeklyPlan and Posts in database
            # Pass existing plan ID if available
            existing_id = existing.id if existing else None
            weekly_plan = await self._save_plan_to_db(plan_data, recent_trends, existing_id)
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

    async def _save_plan_to_db(self, plan_data: Dict, trends: List[Trend], existing_plan_id: int = None) -> WeeklyPlan:
        logger.info("Saving weekly plan to database...")
        
        # Calculate week start (Monday of current week)
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        
        async with async_session() as session:
            async with session.begin():
                if existing_plan_id:
                    result = await session.execute(select(WeeklyPlan).where(WeeklyPlan.id == existing_plan_id))
                    weekly_plan = result.scalar_one()
                else:
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