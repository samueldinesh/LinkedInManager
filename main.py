import asyncio
import logging
from dotenv import load_dotenv

from agents.trend_discovery import TrendDiscoveryAgent
from agents.content_strategy import ContentStrategyAgent
from agents.writing_team import WritingTeam
from core.rate_limiter import RateLimiter
from core.database import create_tables

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting LinkedIn Content Agency...")
    
    # Initialize database
    await create_tables()
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(calls=15, period=60)
    
    # Step 1: Discover trends
    trend_agent = TrendDiscoveryAgent(rate_limiter)
    trends = await trend_agent.discover_trends()
    logger.info(f"Discovered {len(trends)} trends")
    
    # Step 2: Create weekly plan
    strategy_agent = ContentStrategyAgent(rate_limiter)
    plan = await strategy_agent.create_weekly_plan()
    if plan:
        logger.info(f"Created weekly plan with ID {plan.id}")
    else:
        logger.warning("No weekly plan created")
        return
    
    # Step 3: Generate content for posts
    writing_team = WritingTeam(rate_limiter)
    await writing_team.generate_all_draft_posts()
    logger.info("Content generation completed")
    
    # Note: Posting to LinkedIn would be done manually or via dashboard approval
    # For automated posting, you could add a scheduler here
    
    logger.info("LinkedIn Content Agency workflow completed")

if __name__ == "__main__":
    asyncio.run(main())