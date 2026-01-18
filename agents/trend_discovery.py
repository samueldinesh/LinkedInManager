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
        """Call LLM using intelligent API pool (Gemma first, then Gemini)"""
        async with self.rate_limiter:
            # Uses API pool: tries Gemma (14.4K RPD) first, then Gemini (20 RPD)
            response = await call_llm(prompt)
            return response

    async def search_web(self, query: str) -> str:
        # This function will be called by Gemini model via tool_code
        # In a real scenario, this would use a dedicated web search API (e.g., Google Custom Search, SerpApi)
        # For this implementation, we will simulate a web search.
        logger.info(f"Simulating web search for: {query}")
        # In a real application, you would make an actual API call here
        return f"Simulated search results for '{query}': No real results fetched."

    async def discover_trends(self) -> List[Dict]:
        logger.info("Starting trend discovery...")
        queries = [
            "latest quantum computing breakthroughs",
            "quantum computing news India",
            "government schemes for quantum technology India",
            "international quantum computing funding",
            "AI in quantum computing advancements",
            "IoT in quantum computing applications",
            "bioinformatics quantum computing research"
        ]

        discovered_trends = []

        for query in queries:
            prompt = f"Using web search, find the latest information on: {query}. Summarize the top 3 most relevant findings, including a title, a brief description, the likely category (breakthrough, scheme, news, lesson), and if possible, a source URL and region (India, international, global)."
            
            # This is a placeholder for actual Gemini tool calling. 
            # Gemini will invoke the `search_web` function defined in `tools`.
            # For now, we'll directly call `_call_gemini_with_rate_limit` with a simple prompt.
            try:
                response_text = await self._call_llm_with_rate_limit(prompt)
                # Parse response_text into structured trends
                # This parsing logic will need to be more robust
                parsed_trends = self._parse_llm_response(response_text, query)
                discovered_trends.extend(parsed_trends)
            except Exception as e:
                logger.error(f"Error discovering trend for query '{query}': {e}")
        
        await self._save_trends_to_db(discovered_trends)
        return discovered_trends

    def _parse_llm_response(self, response_text: str, query: str) -> List[Dict]:
        # Placeholder for robust parsing logic
        # In a real scenario, you'd use regex or more sophisticated NLP to extract structured data
        logger.info(f"Parsing Gemini response for query '{query}'")
        # Example: if Gemini returns a list of JSON-like strings
        try:
            # Simplified parsing: assuming Gemini directly provides a JSON-like string
            # This is highly dependent on how you prompt Gemini to structure its output
            # For demonstration, let's assume a very basic structure or just extract the summary
            return [{
                "title": f"Summary for {query}",
                "description": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                "category": "news", # Default category, should be smarter
                "source_url": "",
                "region": "global" # Default region, should be smarter
            }]
        except Exception as e:
            logger.warning(f"Could not parse Gemini response for query '{query}': {e}. Returning raw response as a single trend.")
            return [{
                "title": f"Raw response for {query}",
                "description": response_text,
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