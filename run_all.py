"""
Combined runner for LinkedIn AI Manager.

This script runs both the FastAPI dashboard and the background agent scheduler
in a single process using threading.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.trend_discovery import TrendDiscoveryAgent
from agents.content_strategy import ContentStrategyAgent
from agents.writing_team import WritingTeam
from core.rate_limiter import RateLimiter
from core.database import create_tables
from core.plugin_manager import PluginManager
from core.api_pool import APIPool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LinkedInAIManager:
    """Main application coordinator"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.plugin_manager = PluginManager()
        self.api_pool = None
        
    async def initialize(self):
        """Initialize the system"""
        logger.info("Initializing LinkedIn AI Manager...")
        
        # Create database tables
        await create_tables()
        
        # Discover plugins
        self.plugin_manager.discover_plugins()
        
        # Setup API pool with Gemini providers
        await self.setup_api_pool()
        
        logger.info("✓ Initialization complete")
    
    async def setup_api_pool(self):
        """Setup API pool with available providers"""
        self.api_pool = APIPool(routing_strategy="round_robin")
        
        try:
            # Add Gemini providers (3 models for 60 RPD total)
            models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3-flash"]
            
            for i, model in enumerate(models):
                try:
                    provider = self.plugin_manager.get_llm_provider(
                        "gemini",
                        model_name=model,
                        enable_search=False
                    )
                    self.api_pool.add_provider(provider, priority=10-i)
                    logger.info(f"✓ Added {model} to API pool")
                except Exception as e:
                    logger.warning(f"Could not add {model}: {e}")
            
            # Log pool status
            status = self.api_pool.get_pool_status()
            logger.info(f"API Pool: {status['active_providers']}/{status['total_providers']} providers active")
            logger.info(f"Total daily capacity: {self.api_pool.get_total_daily_capacity()} requests")
            
        except Exception as e:
            logger.error(f"Failed to setup API pool: {e}")
    
    async def run_agents(self):
        """Run the agent workflow"""
        logger.info("=" * 60)
        logger.info("Starting agent workflow...")
        logger.info("=" * 60)
        
        try:
            # Initialize rate limiter
            rate_limiter = RateLimiter(calls=15, period=60)
            
            # Step 1: Discover trends
            logger.info("Step 1: Discovering trends...")
            trend_agent = TrendDiscoveryAgent(rate_limiter)
            trends = await trend_agent.discover_trends()
            logger.info(f"✓ Discovered {len(trends)} trends")
            
            # Step 2: Create weekly plan
            logger.info("Step 2: Creating weekly plan...")
            strategy_agent = ContentStrategyAgent(rate_limiter)
            plan = await strategy_agent.create_weekly_plan()
            if plan:
                logger.info(f"✓ Created weekly plan with ID {plan.id}")
            else:
                logger.warning("No weekly plan created")
                return
            
            # Step 3: Generate content
            logger.info("Step 3: Generating content...")
            writing_team = WritingTeam(rate_limiter)
            await writing_team.generate_all_draft_posts()
            logger.info("✓ Content generation completed")
            
            logger.info("=" * 60)
            logger.info("Agent workflow completed successfully!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Agent workflow failed: {e}", exc_info=True)
    
    def schedule_agents(self):
        """Schedule agent runs"""
        # Run agents daily at 9:00 AM
        self.scheduler.add_job(
            self.run_agents,
            CronTrigger(hour=9, minute=0),
            id='daily_agent_run',
            name='Daily Agent Workflow',
            replace_existing=True
        )
        
        logger.info("✓ Scheduled daily agent run at 9:00 AM")
        
        # Optional: Run immediately on startup (for testing)
        # Uncomment the next line to run agents on startup
        # self.scheduler.add_job(self.run_agents, 'date', run_date=datetime.now())
    
    async def start(self):
        """Start the scheduler"""
        await self.initialize()
        self.schedule_agents()
        self.scheduler.start()
        logger.info("✓ Scheduler started")


def run_dashboard():
    """Run the FastAPI dashboard in a separate thread"""
    logger.info("Starting FastAPI dashboard on http://0.0.0.0:8000")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("LinkedIn AI Manager - Combined Runner")
    logger.info("=" * 60)
    
    # Start dashboard in background thread
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    logger.info("✓ Dashboard thread started")
    
    # Give dashboard time to start
    await asyncio.sleep(2)
    
    # Initialize and start agent scheduler
    manager = LinkedInAIManager()
    await manager.start()
    
    logger.info("=" * 60)
    logger.info("System is running!")
    logger.info("Dashboard: http://localhost:8000")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        manager.scheduler.shutdown()
        logger.info("✓ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
