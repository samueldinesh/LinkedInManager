
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from duckduckgo_search import DDGS
from core.interfaces import SearchProvider, ProviderError

logger = logging.getLogger(__name__)

class DuckDuckGoSearchProvider(SearchProvider):
    """
    Search provider using DuckDuckGo (Free).
    """
    
    PLUGIN_NAME = "duckduckgo_search"
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.ddgs = DDGS()

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform a search query using DuckDuckGo.
        
        Args:
            query: Search query string
            **kwargs: 
                - num_results (default: 5)
                - region (default: "wt-wt")
        
        Returns:
            List of search results
        """
        num_results = kwargs.get("num_results", self.max_results)
        region = kwargs.get("region", "wt-wt") # wt-wt is global
        
        try:
            # DDGS is synchronous, so we run it in an executor
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: list(self.ddgs.text(query, region=region, max_results=num_results))
            )
            
            formatted_results = []
            for res in results:
                formatted_results.append({
                    "title": res.get("title", ""),
                    "description": res.get("body", ""),
                    "url": res.get("href", ""),
                    "source": "duckduckgo",
                    "published_date": None # DDG doesn't rarely provide this reliably in free tier
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise ProviderError(f"DuckDuckGo search failed: {e}")

    def get_provider_name(self) -> str:
        return "duckduckgo"

    async def test_connection(self) -> bool:
        """Test connectivity"""
        try:
            await self.search("test", num_results=1)
            return True
        except Exception as e:
            logger.error(f"DuckDuckGo connection test failed: {e}")
            return False
