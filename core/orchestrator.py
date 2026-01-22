"""
Intelligent agent orchestrator with quota management and granular control.
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from core.rate_limiter import RateLimiter
from core.plugin_manager import PluginManager
from core.api_pool import APIPool
from core.interfaces import QuotaExceededError

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Intelligent orchestrator for running agents with quota management.
    """
    
    def __init__(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.api_pool = None
        self.rate_limiter = RateLimiter(calls=15, period=60)
        
        # Real-time status tracking
        self.status = {
            "is_running": False,
            "current_step": "idle",
            "progress": 0,
            "logs": [],
            "last_updated": datetime.now().isoformat()
        }
        
    def _update_status(self, step: str, progress: int, log_message: str = None):
        """Update the global workflow status"""
        self.status["current_step"] = step
        self.status["progress"] = progress
        self.status["last_updated"] = datetime.now().isoformat()
        if log_message:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status["logs"].append(f"[{timestamp}] {log_message}")
            # Keep only last 50 logs
            if len(self.status["logs"]) > 50:
                self.status["logs"].pop(0)

    def get_status(self):
        """Get current workflow status"""
        return self.status

    def clear_logs(self):
        """Clear logs before new run"""
        self.status["logs"] = []
        self.status["is_running"] = True
        self.status["progress"] = 0
        self._update_status("Starting...", 0, "Initializing workflow...")
        
    async def setup_api_pool(self):
        """Setup API pool with verified available models"""
        self.api_pool = APIPool(routing_strategy="priority")
        
        # STRATEGY: 
        # 1. Gemma 3 (High Quota) for most tasks
        # 2. Gemini 2.0 (Quality) for complex tasks
        
        # HIGH PRIORITY: verified Gemma 3 models
        gemma_models = [
            ("gemma-3-4b-it", 90),       # 4B Instruct - PRIMARY
            ("gemma-3-12b-it", 95),       # 12B Instruct - High Quality Backup
            ("gemma-3-27b-it", 100),       # 27B Instruct - Maximum Quality Backup
        ]
        
        for model_name, priority in gemma_models:
            try:
                provider = self.plugin_manager.get_llm_provider(
                    "gemma",
                    model_name=model_name
                )
                self.api_pool.add_provider(provider, priority=priority)
                logger.info(f"✓ Added {model_name} (High Quota) - Priority {priority}")
            except Exception as e:
                logger.warning(f"Could not add {model_name}: {e}")
        
        # MEDIUM PRIORITY: verified Gemini models
        gemini_models = [
            ("gemini-2.0-flash", 50),       # Standard Flash
            ("gemini-2.0-flash-lite", 45),  # Lite version
            ("gemini-2.5-flash-lite", 40),  # Newer Lite version
        ]
        
        for model_name, priority in gemini_models:
            try:
                # Enable search for the standard flash model
                enable_search = (model_name == "gemini-2.0-flash")
                
                provider = self.plugin_manager.get_llm_provider(
                    "gemini",
                    model_name=model_name,
                    enable_search=enable_search
                )
                self.api_pool.add_provider(provider, priority=priority)
                
                search_status = " (Search Enabled)" if enable_search else ""
                logger.info(f"✓ Added {model_name} (20 RPD) - Priority {priority}{search_status}")
            except Exception as e:
                logger.warning(f"Could not add {model_name}: {e}")
        
        # Log pool status
        status = self.api_pool.get_pool_status()
        total_capacity = self.api_pool.get_total_daily_capacity()
        
        logger.info("=" * 60)
        logger.info(f"API Pool Configuration:")
        logger.info(f"  Active Providers: {status['active_providers']}/{status['total_providers']}")
        logger.info(f"  Total Daily Capacity: {total_capacity:,} requests/day")
        logger.info(f"  Strategy: Gemma 3 (Basic) → Gemini 2.0 (Quality)")
        logger.info("=" * 60)
    
    async def run_trend_discovery(self) -> dict:
        """
        Run only trend discovery.
        """
        # Lazy import to avoid circular dependency
        from agents.trend_discovery import TrendDiscoveryAgent
        
        self._update_status("Trend Discovery", 10, "Starting Trend Discovery Agent...")
        logger.info("=" * 60)
        logger.info("STEP 1: Trend Discovery")
        logger.info("=" * 60)
        
        try:
            trend_agent = TrendDiscoveryAgent(self.rate_limiter)
            self._update_status("Trend Discovery", 20, "Searching for latest trends...")
            trends = await trend_agent.discover_trends()
            
            self._update_status("Trend Discovery", 30, f"✅ Found {len(trends)} new trends.")
            
            return {
                "success": True,
                "step": "trend_discovery",
                "trends_found": len(trends),
                "message": f"Discovered {len(trends)} trends"
            }
        except QuotaExceededError as e:
            self._update_status("Error", 0, f"❌ Quota Exceeded: {e}")
            logger.error(f"Quota exceeded during trend discovery: {e}")
            return {
                "success": False,
                "step": "trend_discovery",
                "error": "quota_exceeded",
                "message": "Daily quota exceeded."
            }
        except Exception as e:
            self._update_status("Error", 0, f"❌ Error: {e}")
            logger.error(f"Error in trend discovery: {e}", exc_info=True)
            return {
                "success": False,
                "step": "trend_discovery",
                "error": str(e),
                "message": f"Failed: {str(e)}"
            }
    
    async def run_content_strategy(self) -> dict:
        """
        Run only content strategy (create weekly plan).
        """
        # Lazy import to avoid circular dependency
        from agents.content_strategy import ContentStrategyAgent
        
        self._update_status("Content Strategy", 40, "Starting Content Strategy Agent...")
        logger.info("=" * 60)
        logger.info("STEP 2: Content Strategy")
        logger.info("=" * 60)
        
        try:
            strategy_agent = ContentStrategyAgent(self.rate_limiter)
            self._update_status("Content Strategy", 50, "Creating weekly plan...")
            plan = await strategy_agent.create_weekly_plan()
            
            if plan:
                self._update_status("Content Strategy", 60, "✅ Weekly plan created successfully.")
                return {
                    "success": True,
                    "step": "content_strategy",
                    "plan_id": plan.id,
                    "message": f"Created weekly plan (ID: {plan.id})"
                }
            else:
                self._update_status("Content Strategy", 60, "⚠ No plan created (no trends found).")
                return {
                    "success": False,
                    "step": "content_strategy",
                    "error": "no_plan_created",
                    "message": "No plan was created. Check if trends exist."
                }
        except QuotaExceededError as e:
            self._update_status("Error", 0, f"❌ Quota Exceeded: {e}")
            logger.error(f"Quota exceeded during strategy: {e}")
            return {
                "success": False,
                "step": "content_strategy",
                "error": "quota_exceeded",
                "message": "Daily quota exceeded."
            }
        except Exception as e:
            self._update_status("Error", 0, f"❌ Error: {e}")
            logger.error(f"Error in content strategy: {e}", exc_info=True)
            return {
                "success": False,
                "step": "content_strategy",
                "error": str(e),
                "message": f"Failed: {str(e)}"
            }
    
    async def run_content_generation(self) -> dict:
        """
        Run only content generation (write posts).
        """
        # Lazy import to avoid circular dependency
        from agents.writing_team import WritingTeam
        
        self._update_status("Content Generation", 70, "Starting Content Generation Agent...")
        logger.info("=" * 60)
        logger.info("STEP 3: Content Generation")
        logger.info("=" * 60)
        
        try:
            writing_team = WritingTeam(self.rate_limiter)
            self._update_status("Content Generation", 80, "Generating content for posts...")
            await writing_team.generate_all_draft_posts()
            
            self._update_status("Complete", 100, "✅ All content generated successfully!")
            self.status["is_running"] = False
            
            return {
                "success": True,
                "step": "content_generation",
                "message": "Content generated for all draft posts"
            }
        except QuotaExceededError as e:
            self._update_status("Error", 0, f"❌ Quota Exceeded: {e}")
            logger.error(f"Quota exceeded during generation: {e}")
            return {
                "success": False,
                "step": "content_generation",
                "error": "quota_exceeded",
                "message": "Daily quota exceeded."
            }
        except Exception as e:
            self._update_status("Error", 0, f"❌ Error: {e}")
            logger.error(f"Error in content generation: {e}", exc_info=True)
            return {
                "success": False,
                "step": "content_generation",
                "error": str(e),
                "message": f"Failed: {str(e)}"
            }
    
    async def run_full_workflow(self, steps: Optional[List[str]] = None) -> dict:
        """
        Run the complete workflow or selected steps.
        
        Args:
            steps: List of steps to run. Options: 
                   ['trends', 'strategy', 'content']
                   If None, runs all steps.
        
        Returns:
            dict with overall status and results
        """
        if steps is None:
            steps = ['trends', 'strategy', 'content']
        
        logger.info("=" * 60)
        logger.info(f"Starting workflow with steps: {', '.join(steps)}")
        logger.info("=" * 60)
        
        results = {
            "success": True,
            "steps_completed": [],
            "steps_failed": [],
            "details": {}
        }
        
        # Step 1: Trend Discovery
        if 'trends' in steps:
            result = await self.run_trend_discovery()
            results["details"]["trends"] = result
            
            if result["success"]:
                results["steps_completed"].append("trends")
            else:
                results["steps_failed"].append("trends")
                if result.get("error") == "quota_exceeded":
                    # Stop if quota exceeded
                    results["success"] = False
                    results["message"] = "Workflow stopped: Quota exceeded"
                    return results
        
        # Step 2: Content Strategy
        if 'strategy' in steps:
            result = await self.run_content_strategy()
            results["details"]["strategy"] = result
            
            if result["success"]:
                results["steps_completed"].append("strategy")
            else:
                results["steps_failed"].append("strategy")
                if result.get("error") == "quota_exceeded":
                    results["success"] = False
                    results["message"] = "Workflow stopped: Quota exceeded"
                    return results
        
        # Step 3: Content Generation
        if 'content' in steps:
            result = await self.run_content_generation()
            results["details"]["content"] = result
            
            if result["success"]:
                results["steps_completed"].append("content")
            else:
                results["steps_failed"].append("content")
        
        # Overall status
        if results["steps_failed"]:
            results["success"] = False
            results["message"] = f"Completed {len(results['steps_completed'])}/{len(steps)} steps"
        else:
            results["message"] = f"All {len(steps)} steps completed successfully"
        
        logger.info("=" * 60)
        logger.info(f"Workflow complete: {results['message']}")
        logger.info("=" * 60)
        
        return results


# Global instance
orchestrator = AgentOrchestrator()
