"""
Abstract interfaces for the LinkedIn AI Manager plugin system.

This module defines the core interfaces that all plugins must implement,
enabling a modular, extensible architecture.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ProviderStatus(Enum):
    """Status of an API provider"""
    ACTIVE = "active"
    QUOTA_EXCEEDED = "quota_exceeded"
    ERROR = "error"
    DISABLED = "disabled"


class LLMProvider(ABC):
    """
    Abstract interface for Language Model providers.
    
    All LLM providers (Gemini, OpenAI, Anthropic, etc.) must implement this interface.
    """
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)
            
        Returns:
            Generated text response
            
        Raises:
            QuotaExceededError: When API quota is exhausted
            ProviderError: For other provider-specific errors
        """
        pass
    
    @abstractmethod
    def get_quota_info(self) -> Dict[str, Any]:
        """
        Get current quota information.
        
        Returns:
            Dictionary with keys:
                - requests_used: int
                - requests_remaining: int
                - daily_limit: int
                - reset_time: datetime
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model identifier (e.g., 'gemini-2.5-flash-lite')"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name (e.g., 'gemini', 'openai')"""
        pass
    
    @abstractmethod
    def get_status(self) -> ProviderStatus:
        """Get current provider status"""
        pass
    
    @abstractmethod
    def supports_search(self) -> bool:
        """
        Check if the provider supports web search grounding.
        
        Returns:
            True if search is enabled
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the provider is accessible and credentials are valid.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass


class SearchProvider(ABC):
    """
    Abstract interface for Search providers.
    
    Supports web search, news search, and other information retrieval.
    """
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform a search query.
        
        Args:
            query: Search query string
            **kwargs: Provider-specific parameters (num_results, region, etc.)
            
        Returns:
            List of search results, each containing:
                - title: str
                - description: str
                - url: str
                - published_date: Optional[datetime]
                - source: str
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the search provider name"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the search provider is accessible"""
        pass


class ContentStrategy(ABC):
    """
    Abstract interface for content planning strategies.
    
    Different strategies can be implemented for different topics or styles.
    """
    
    @abstractmethod
    async def generate_plan(
        self, 
        trends: List[Dict[str, Any]], 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a content plan based on discovered trends.
        
        Args:
            trends: List of discovered trends
            config: Strategy configuration (content mix, frequency, etc.)
            
        Returns:
            Content plan dictionary with:
                - posts: List[Dict] - planned posts
                - schedule: Dict - posting schedule
                - metadata: Dict - additional planning info
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the strategy identifier"""
        pass
    
    @abstractmethod
    def get_supported_categories(self) -> List[str]:
        """Get list of content categories this strategy supports"""
        pass


class PlatformConnector(ABC):
    """
    Abstract interface for social media platform connectors.
    
    Supports posting to LinkedIn, Twitter, Facebook, etc.
    """
    
    @abstractmethod
    async def post(self, content: str, **kwargs) -> Dict[str, Any]:
        """
        Post content to the platform.
        
        Args:
            content: The text content to post
            **kwargs: Platform-specific parameters (images, links, etc.)
            
        Returns:
            Dictionary with:
                - success: bool
                - post_id: Optional[str]
                - url: Optional[str]
                - error: Optional[str]
        """
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the platform.
        
        Returns:
            True if authentication successful
        """
        pass
    
    @abstractmethod
    async def get_auth_url(self) -> str:
        """
        Get OAuth authorization URL for user authentication.
        
        Returns:
            Authorization URL
        """
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the platform name (e.g., 'linkedin', 'twitter')"""
        pass


# Custom Exceptions

class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class QuotaExceededError(ProviderError):
    """Raised when API quota is exceeded"""
    pass


class AuthenticationError(ProviderError):
    """Raised when authentication fails"""
    pass


class PluginLoadError(Exception):
    """Raised when a plugin fails to load"""
    pass
