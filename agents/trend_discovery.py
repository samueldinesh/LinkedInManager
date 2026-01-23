import os
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict

from core.database import async_session
from core.database import async_session
from core.models import Trend, ContentTopic
from core.rate_limiter import RateLimiter
from core.llm_caller import call_llm
from plugins.search_providers.duckduckgo_provider import DuckDuckGoSearchProvider
from sqlalchemy import select

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrendDiscoveryAgent:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.search_provider = DuckDuckGoSearchProvider()

    async def _call_llm_with_rate_limit(self, prompt: str) -> str:
        """
        Call LLM for trend discovery.
        
        STRATEGY UPDATE:
        Due to Gemini quota issues, we default to "Internal Knowledge" (Gemma).
        We request 'require_search=False' so the Orchestrator picks the highest priority model (Gemma).
        """
        async with self.rate_limiter:
            try:
                # Default: Use Internal Knowledge (Gemma)
                # require_search=False allows Gemma (Priority 100) to be picked over Gemini (Priority 50)
                response = await call_llm(prompt, require_search=False)
                return response
            except Exception as e:
                logger.error(f"Trend discovery generation failed: {e}")
                raise

    async def _get_search_queries(self) -> List[str]:
        """Fetch search queries from active ContentTopics or seed defaults."""
        async with async_session() as session:
            # Fetch active topics
            result = await session.execute(
                select(ContentTopic).where(ContentTopic.is_active == True)
            )
            topics = result.scalars().all()
            
            if topics:
                queries = []
                for topic in topics:
                    # Flatten list of lists
                    if isinstance(topic.search_queries, list):
                        queries.extend(topic.search_queries)
                return queries
            
            # Fallback/Seed: Create default topics if none exist
            logger.info("No active topics found. Seeding default topics...")
            default_topics = [
                ContentTopic(
                    name="Quantum Computing",
                    description="Latest updates in Quantum Tech",
                    search_queries=[
                        "latest quantum computing breakthroughs this week",
                        "quantum computing news India latest",
                        "government schemes for quantum technology India 2025",
                        "international quantum computing funding news"
                    ],
                    is_active=True
                ),
                ContentTopic(
                    name="Deep Tech AI",
                    description="Intersection of AI and Hard Tech",
                    search_queries=[
                        "AI in quantum computing latest advancements",
                        "IoT in quantum computing applications news",
                        "bioinformatics quantum computing research updates"
                    ],
                    is_active=True
                )
            ]
            
            session.add_all(default_topics)
            await session.commit()
            
            # Return flattened defaults
            return [q for t in default_topics for q in t.search_queries]

    async def discover_trends(self) -> List[Dict]:
        logger.info("Starting trend discovery with Google Search...")
        
        # Get queries dynamically
        queries = await self._get_search_queries()
        logger.info(f"Found {len(queries)} search queries to process.")

        discovered_trends = []

        for query in queries:
            try:
                # 1. Search with DuckDuckGo
                logger.info(f"Searching for: {query}")
                search_results = await self.search_provider.search(query)
                search_context = "\n".join([f"- {r['title']}: {r['description']} (Source: {r['url']})" for r in search_results])
                
                # 2. Generate with Gemma
                prompt = f"""
Analyze these search results for "{query}":
{search_context}

Extract the top 3 most relevant findings and return them as a JSON array.

For each finding, include:
- "title": A clear, concise headline
- "description": 2-3 sentences explaining what happened and why it matters
- "category": One of: "breakthrough", "scheme", "news", or "lesson"
- "source_url": The URL from the search results (or "N/A" if not available)
- "region": One of: "India", "International", or "Global"

IMPORTANT: You MUST respond with ONLY valid JSON. No explanations, no markdown, no text before or after the JSON.

Example output format:
[
  {{
    "title": "Example Title",
    "description": "Example description of the finding.",
    "category": "news",
    "source_url": "https://example.com",
    "region": "India"
  }}
]
"""
                
                # Generate with Gemma
                response_text = await self._call_llm_with_rate_limit(prompt)
                # Parse response_text into structured trends
                parsed_trends = self._parse_llm_response(response_text, query)
                discovered_trends.extend(parsed_trends)
                
                # Add delay to smooth out traffic
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error discovering trend for query '{query}': {e}")
                # Wait a bit longer on error
                await asyncio.sleep(5)
        
        await self._save_trends_to_db(discovered_trends)
        return discovered_trends

    def _parse_llm_response(self, response_text: str, query: str) -> List[Dict]:
        """Parse JSON response from LLM with robust fallback."""
        import json
        import re
        
        text = response_text.strip()
        
        # Step 1: Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
        
        text = text.strip()
        
        # Step 2: Try direct JSON parse
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = [data]
            return self._validate_trends(data)
        except json.JSONDecodeError:
            pass
        
        # Step 3: Regex fallback - find JSON array in text
        try:
            array_match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
            if array_match:
                data = json.loads(array_match.group())
                return self._validate_trends(data)
        except:
            pass
        
        # Step 4: Regex fallback - find individual JSON objects
        try:
            pattern = r'\{[^{}]*"title"[^{}]*\}'
            matches = re.findall(pattern, text, re.DOTALL)
            results = []
            for match in matches:
                try:
                    obj = json.loads(match)
                    if "title" in obj:
                        results.append(obj)
                except:
                    continue
            if results:
                return self._validate_trends(results)
        except:
            pass
        
        # Final fallback: Create a single item from raw text
        logger.warning(f"All JSON parsing failed for query '{query}'. Using text fallback.")
        return [{
            "title": f"Trends for {query}",
            "description": text[:500] if text else response_text[:500],
            "category": "news",
            "source_url": "",
            "region": "global"
        }]
    
    def _validate_trends(self, data: List[Dict]) -> List[Dict]:
        """Validate and normalize trend objects."""
        valid_trends = []
        for item in data:
            if isinstance(item, dict) and "title" in item and "description" in item:
                item["category"] = item.get("category", "news").lower()
                item["region"] = item.get("region", "global")
                item["source_url"] = item.get("source_url", "")
                valid_trends.append(item)
        return valid_trends

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