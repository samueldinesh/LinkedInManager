
import asyncio
import logging
import os
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.database import create_tables
from core.rate_limiter import RateLimiter
from core.plugin_manager import PluginManager
from core.api_pool import APIPool

# Import Agents
from agents.trend_discovery import TrendDiscoveryAgent
from agents.content_strategy import ContentStrategyAgent
from agents.writing_team import WritingTeam

async def verify_full_workflow():
    logger.info("="*60)
    logger.info("STARTING FULL END-TO-END VERIFICATION")
    logger.info("="*60)

    # 1. Setup Environment
    await create_tables()
    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()
    
    # Setup API Pool (Mocking orchestration logic)
    # We rely on the global providers having been fixed to use priority
    
    rate_limiter = RateLimiter(calls=15, period=60)

    # 2. Run Trend Discovery
    logger.info("\n--- STEP 1: TREND DISCOVERY (DuckDuckGo + Gemma) ---")
    trend_agent = TrendDiscoveryAgent(rate_limiter)
    trends = await trend_agent.discover_trends()
    logger.info(f"Trends Discovered: {len(trends)}")
    if not trends:
        logger.error("FAILED: No trends found.")
        return

    # 3. Run Content Strategy
    logger.info("\n--- STEP 2: CONTENT STRATEGY (Gemma) ---")
    strategy_agent = ContentStrategyAgent(rate_limiter)
    plan = await strategy_agent.create_weekly_plan()
    if plan:
        logger.info(f"Weekly Plan Created: ID {plan.id} for week starting {plan.week_start}")
    else:
        logger.error("FAILED: No weekly plan created.")
        return

    # 4. Run Writing Team
    logger.info("\n--- STEP 3: WRITING TEAM (Gemma Async) ---")
    writing_team = WritingTeam(rate_limiter)
    await writing_team.generate_all_draft_posts()
    logger.info("Content Generation Completed.")

    logger.info("="*60)
    logger.info("VERIFICATION SUCCESSFUL: All steps completed without error.")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(verify_full_workflow())
