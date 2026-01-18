"""
Test script for the plugin system and API pool.

This script demonstrates:
1. Plugin discovery and loading
2. Gemini provider with quota tracking
3. Gemini search with grounding
4. API pool with multiple providers
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.plugin_manager import PluginManager
from core.api_pool import APIPool
from core.database import create_tables

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_plugin_discovery():
    """Test plugin discovery"""
    logger.info("=" * 60)
    logger.info("TEST 1: Plugin Discovery")
    logger.info("=" * 60)
    
    pm = PluginManager()
    pm.discover_plugins()
    
    plugins = pm.list_plugins()
    logger.info(f"\nDiscovered plugins:")
    for category, plugin_list in plugins.items():
        logger.info(f"  {category}: {plugin_list}")
    
    return pm


async def test_gemini_provider(pm: PluginManager):
    """Test Gemini LLM provider"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Gemini LLM Provider")
    logger.info("=" * 60)
    
    try:
        # Create Gemini provider
        gemini = pm.get_llm_provider(
            "gemini",
            model_name="gemini-2.5-flash-lite",
            enable_search=False
        )
        
        logger.info(f"\nProvider: {gemini.get_provider_name()}")
        logger.info(f"Model: {gemini.get_model_name()}")
        logger.info(f"Status: {gemini.get_status()}")
        
        # Check quota
        quota = gemini.get_quota_info()
        logger.info(f"\nQuota Info:")
        logger.info(f"  Used: {quota['requests_used']}")
        logger.info(f"  Remaining: {quota['requests_remaining']}")
        logger.info(f"  Daily Limit: {quota['daily_limit']}")
        logger.info(f"  Reset Time: {quota['reset_time']}")
        
        # Test connection
        logger.info("\nTesting connection...")
        connected = await gemini.test_connection()
        logger.info(f"Connection test: {'✓ PASSED' if connected else '✗ FAILED'}")
        
        # Generate some text
        if connected:
            logger.info("\nGenerating text...")
            response = await gemini.generate(
                "Explain quantum computing in one sentence."
            )
            logger.info(f"Response: {response[:200]}...")
            
            # Check updated quota
            quota = gemini.get_quota_info()
            logger.info(f"\nUpdated Quota:")
            logger.info(f"  Used: {quota['requests_used']}")
            logger.info(f"  Remaining: {quota['requests_remaining']}")
        
        return gemini
        
    except Exception as e:
        logger.error(f"Gemini provider test failed: {e}")
        return None


async def test_gemini_search(pm: PluginManager):
    """Test Gemini search provider"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Gemini Search Provider")
    logger.info("=" * 60)
    
    try:
        # Create search provider
        search = pm.get_search_provider("gemini_search")
        
        logger.info(f"\nProvider: {search.get_provider_name()}")
        
        # Test connection
        logger.info("\nTesting connection...")
        connected = await search.test_connection()
        logger.info(f"Connection test: {'✓ PASSED' if connected else '✗ FAILED'}")
        
        # Perform a search
        if connected:
            logger.info("\nSearching for: 'latest quantum computing breakthroughs 2026'")
            results = await search.search(
                "latest quantum computing breakthroughs 2026",
                num_results=3
            )
            
            logger.info(f"\nFound {len(results)} results:")
            for i, result in enumerate(results, 1):
                logger.info(f"\n  Result {i}:")
                logger.info(f"    Title: {result.get('title', 'N/A')}")
                logger.info(f"    Description: {result.get('description', 'N/A')[:150]}...")
                logger.info(f"    URL: {result.get('url', 'N/A')}")
                logger.info(f"    Source: {result.get('source', 'N/A')}")
        
        return search
        
    except Exception as e:
        logger.error(f"Search provider test failed: {e}")
        return None


async def test_api_pool(gemini_provider):
    """Test API pool with multiple providers"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: API Pool")
    logger.info("=" * 60)
    
    try:
        # Create API pool
        pool = APIPool(routing_strategy="round_robin")
        
        # Add Gemini provider
        if gemini_provider:
            pool.add_provider(gemini_provider, priority=10)
        
        # You could add more providers here:
        # pool.add_provider(openai_provider, priority=5)
        # pool.add_provider(ollama_provider, priority=1)
        
        # Get pool status
        status = pool.get_pool_status()
        logger.info(f"\nPool Status:")
        logger.info(f"  Total Providers: {status['total_providers']}")
        logger.info(f"  Active Providers: {status['active_providers']}")
        logger.info(f"  Total Daily Capacity: {pool.get_total_daily_capacity()}")
        
        logger.info(f"\nProviders in pool:")
        for provider in status['providers']:
            logger.info(f"  - {provider['name']} ({provider['model']})")
            logger.info(f"    Status: {provider['status']}")
            logger.info(f"    Priority: {provider['priority']}")
            logger.info(f"    Quota: {provider['quota']['requests_remaining']}/{provider['quota']['daily_limit']}")
        
        # Test routing
        logger.info("\nTesting API pool routing...")
        response = await pool.call("What is the capital of France?")
        logger.info(f"Response: {response}")
        
        return pool
        
    except Exception as e:
        logger.error(f"API pool test failed: {e}")
        return None


async def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("LinkedIn AI Manager - Plugin System Test")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("\nInitializing database...")
    await create_tables()
    logger.info("✓ Database initialized")
    
    # Test 1: Plugin Discovery
    pm = await test_plugin_discovery()
    
    # Test 2: Gemini Provider
    gemini = await test_gemini_provider(pm)
    
    # Test 3: Gemini Search
    search = await test_gemini_search(pm)
    
    # Test 4: API Pool
    if gemini:
        pool = await test_api_pool(gemini)
    
    logger.info("\n" + "=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
