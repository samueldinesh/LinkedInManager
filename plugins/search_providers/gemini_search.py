"""
Gemini Search Provider using Google Search grounding.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from core.interfaces import SearchProvider, ProviderError

logger = logging.getLogger(__name__)


class GeminiSearchProvider(SearchProvider):
    """
    Search provider using Gemini's built-in Google Search grounding.
    
    This is completely free and provides real-time web search results.
    """
    
    PLUGIN_NAME = "gemini_search"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash-lite"
    ):
        """
        Initialize Gemini Search provider.
        
        Args:
            api_key: Google API key
            model_name: Gemini model to use for search
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY not found")
        
        self.model_name = model_name
        
        # Initialize with search grounding enabled
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=self.api_key,
                temperature=0.3,  # Lower temperature for factual search
                tools=[{"google_search_retrieval": {}}]
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Search: {e}")
            raise ProviderError(f"Failed to initialize Gemini Search: {e}")
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform a search using Gemini's grounding.
        
        Args:
            query: Search query
            **kwargs: Additional parameters
                - num_results: Number of results to return (default: 5)
                - region: Geographic region filter
                
        Returns:
            List of search results with title, description, url, etc.
        """
        num_results = kwargs.get('num_results', 5)
        region = kwargs.get('region', 'global')
        
        # Craft a prompt that instructs Gemini to search and structure results
        prompt = f"""
Search the web for: "{query}"

Please provide the top {num_results} most relevant and recent results.
For each result, extract:
1. Title
2. Brief description/summary
3. Source URL
4. Publication date (if available)
5. Source name

Format your response as a structured list with clear sections for each result.
Focus on recent information (prefer results from the last 6 months if available).
"""
        
        if region and region.lower() != 'global':
            prompt += f"\nPrioritize results relevant to {region}."
        
        try:
            # Call Gemini with search grounding
            response = self.llm.invoke(prompt)
            
            # Parse the response into structured results
            results = self._parse_search_response(response.content, query)
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise ProviderError(f"Search failed: {e}")
    
    def _parse_search_response(self, response_text: str, query: str) -> List[Dict[str, Any]]:
        """
        Parse Gemini's search response into structured results.
        
        This is a heuristic parser. In production, you might want to use
        Gemini's structured output or JSON mode for more reliable parsing.
        """
        results = []
        
        # Split response into sections (basic heuristic)
        lines = response_text.split('\n')
        
        current_result = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_result:
                    results.append(current_result)
                    current_result = {}
                continue
            
            # Try to identify different fields
            lower_line = line.lower()
            
            if lower_line.startswith(('title:', '**title', '1.', '2.', '3.', '4.', '5.')):
                if current_result:
                    results.append(current_result)
                current_result = {
                    'title': line.split(':', 1)[-1].strip().strip('*'),
                    'description': '',
                    'url': '',
                    'published_date': None,
                    'source': 'Google Search via Gemini'
                }
            elif 'description' in lower_line or 'summary' in lower_line:
                current_result['description'] = line.split(':', 1)[-1].strip()
            elif 'url' in lower_line or 'link' in lower_line or 'http' in line:
                # Extract URL
                url = line.split(':', 1)[-1].strip() if ':' in line else line
                current_result['url'] = url.strip()
            elif 'date' in lower_line or 'published' in lower_line:
                current_result['published_date'] = line.split(':', 1)[-1].strip()
            elif 'source' in lower_line:
                current_result['source'] = line.split(':', 1)[-1].strip()
            elif current_result and not current_result.get('description'):
                # Assume it's part of description
                current_result['description'] += ' ' + line
        
        # Add last result
        if current_result:
            results.append(current_result)
        
        # If parsing failed, create a single result with the full response
        if not results:
            results = [{
                'title': f"Search results for: {query}",
                'description': response_text[:500],
                'url': '',
                'published_date': None,
                'source': 'Google Search via Gemini'
            }]
        
        return results
    
    def get_provider_name(self) -> str:
        """Get the search provider name"""
        return "gemini_search"
    
    async def test_connection(self) -> bool:
        """Test if search is working"""
        try:
            results = await self.search("test query", num_results=1)
            return len(results) > 0
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
