import os
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict

from core.database import async_session
from core.models import Trend
from core.rate_limiter import RateLimiter
from core.llm_caller import call_llm
from sqlalchemy import select

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrendDiscoveryAgent:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    async def _call_llm_with_rate_limit(self, prompt: str) -> str:
        """Call LLM with search capability enabled"""
        async with self.rate_limiter:
            # Force using a provider that supports search (Gemini Flash)
            response = await call_llm(prompt, require_search=True)
            return response

    async def discover_trends(self) -> List[Dict]:
        logger.info("Starting trend discovery with Google Search...")
        queries = [
            "latest quantum computing breakthroughs this week",
            "quantum computing news India latest",
            "government schemes for quantum technology India 2025",
            "international quantum computing funding news",
            "AI in quantum computing latest advancements",
            "IoT in quantum computing applications news",
            "bioinformatics quantum computing research updates"
        ]

        discovered_trends = []

        for query in queries:
            prompt = f"""
            Using your search capabilities, find the latest information on: {query}. 
            Summarize the top 3 most relevant findings. 
            
            For each finding, provide:
            1. Title
            2. Brief description (what happened and why it matters)
            3. Category (breakthrough, scheme, news, or lesson)
            4. Source URL (if available)
            5. Region (India, International, or Global)
            
            Format the output strictly as a JSON list of objects.
            Example:
            [
                {{
                    "title": "Example Title",
                    "description": "Example description...",
                    "category": "news",
                    "source_url": "https://example.com",
                    "region": "India"
                }}
            ]
            """
            
            try:
                response_text = await self._call_llm_with_rate_limit(prompt)
                # Parse response_text into structured trends
                parsed_trends = self._parse_llm_response(response_text, query)
                discovered_trends.extend(parsed_trends)
            except Exception as e:
                logger.error(f"Error discovering trend for query '{query}': {e}")
        
        await self._save_trends_to_db(discovered_trends)
        return discovered_trends

    def _parse_llm_response(self, response_text: str, query: str) -> List[Dict]:
        """Parse JSON response from LLM"""
        try:
            import json
            import re
            
            # Clean up: remove markdown code blocks
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            text = text.strip()
            
            # Parse JSON
            data = json.loads(text)
            
            # Ensure it's a list
            if isinstance(data, dict):
                data = [data]
                
            # Validate structure
            valid_trends = []
            for item in data:
                if "title" in item and "description" in item:
                    item["category"] = item.get("category", "news")
                    item["region"] = item.get("region", "global")
                    valid_trends.append(item)
            
            return valid_trends
            
        except Exception as e:
            logger.warning(f"Failed to parse JSON for query '{query}': {e}")
            logger.debug(f"Raw response: {response_text}")
            
            # Fallback: Create a single item from raw text
            return [{
                "title": f"Trends for {query}",
                "description": response_text[:500],
                "category": "news", 
                "source_url": "",
                "region": "global"
            }]

    async def _save_trends_to_db(self, trends: List[Dict]):
        logger.info(f"Saving {len(trends)} discovered trends to database...")
        async with async_session() as session:
            async with session.begin():
                for trend_data in trends:
                    result = await session.execute(
                        select(Trend).filter_by(title=trend_data["title"], category=trend_data["category"])
                    )
                    existing_trend = result.scalar_one_or_none()
                    
                    if not existing_trend:
                        new_trend = Trend(
                            title=trend_data["title"],
                            description=trend_data["description"],
                            category=trend_data["category"],
                            source_url=trend_data.get("source_url"),
                            region=trend_data.get("region", "global")
                        )
                        session.add(new_trend)
                        logger.info(f"Added new trend: {new_trend.title}")
                    else:
                        logger.info(f"Trend already exists, skipping: {existing_trend.title}")
            await session.commit()
        logger.info("Trends saved successfully.")

# Example of how to run the agent
async def run_trend_discovery():
    from core.rate_limiter import RateLimiter # Import locally to avoid circular dependency for now
    rate_limiter = RateLimiter(calls=15, period=60) # 15 requests per minute
    agent = TrendDiscoveryAgent(rate_limiter)
    trends = await agent.discover_trends()
    logger.info(f"Discovered {len(trends)} trends.")

if __name__ == "__main__":
    asyncio.run(run_trend_discovery())