"""
Gemini LLM Provider Plugin with multi-model support and quota tracking.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core import exceptions as google_exceptions

from core.interfaces import LLMProvider, ProviderStatus, QuotaExceededError, ProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Gemini LLM Provider supporting multiple models with quota tracking.
    
    Supports:
    - gemini-2.5-flash-lite (10 RPM, 20 RPD)
    - gemini-2.5-flash (5 RPM, 20 RPD)
    - gemini-3-flash (5 RPM, 20 RPD)
    """
    
    PLUGIN_NAME = "gemini"
    
    # Model configurations
    MODEL_CONFIGS = {
        "gemini-2.5-flash-lite": {"rpm": 10, "rpd": 20, "tpm": 250000},
        "gemini-2.5-flash": {"rpm": 5, "rpd": 20, "tpm": 250000},
        "gemini-3-flash": {"rpm": 5, "rpd": 20, "tpm": 250000},
    }
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash-lite",
        temperature: float = 0.7,
        enable_search: bool = False,
        usage_file: str = "data/gemini_usage.json"
    ):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use
            temperature: Generation temperature
            enable_search: Enable Google Search grounding
            usage_file: Path to usage tracking file
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY not found in environment or parameters")
        
        self.model_name = model_name
        self.temperature = temperature
        self.enable_search = enable_search
        self.usage_file = Path(usage_file)
        
        # Ensure data directory exists
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize usage stats
        self.usage_stats = self._load_usage_stats()
        
        # Initialize LangChain model
        tools = []
        if enable_search:
            tools = [{"google_search_retrieval": {}}]
        
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=self.api_key,
                temperature=temperature,
                tools=tools if tools else None
            )
            self.status = ProviderStatus.ACTIVE
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.status = ProviderStatus.ERROR
            raise ProviderError(f"Failed to initialize Gemini: {e}")
    
    def _load_usage_stats(self) -> Dict[str, Any]:
        """Load usage statistics from file"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    stats = json.load(f)
                    
                # Check if we need to reset daily counters
                last_reset = datetime.fromisoformat(stats.get('last_reset', '2000-01-01'))
                if datetime.utcnow().date() > last_reset.date():
                    stats['daily_requests'] = 0
                    stats['last_reset'] = datetime.utcnow().isoformat()
                    
                return stats
            except Exception as e:
                logger.warning(f"Failed to load usage stats: {e}")
        
        # Initialize new stats
        return {
            'daily_requests': 0,
            'total_requests': 0,
            'last_reset': datetime.utcnow().isoformat(),
            'model': self.model_name
        }
    
    def _save_usage_stats(self):
        """Save usage statistics to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage stats: {e}")
    
    def _increment_usage(self):
        """Increment usage counters"""
        self.usage_stats['daily_requests'] += 1
        self.usage_stats['total_requests'] += 1
        self._save_usage_stats()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Generated text
            
        Raises:
            QuotaExceededError: If daily quota exceeded
            ProviderError: For other errors
        """
        # Check quota
        quota_info = self.get_quota_info()
        if quota_info['requests_remaining'] <= 0:
            self.status = ProviderStatus.QUOTA_EXCEEDED
            raise QuotaExceededError(
                f"Daily quota exceeded for {self.model_name}. "
                f"Resets at {quota_info['reset_time']}"
            )
        
        try:
            # Call the model (temperature is already set in __init__)
            response = self.llm.invoke(prompt)
            
            # Increment usage
            self._increment_usage()
            
            # Update status
            self.status = ProviderStatus.ACTIVE
            
            return response.content
            
        except google_exceptions.ResourceExhausted as e:
            self.status = ProviderStatus.QUOTA_EXCEEDED
            raise QuotaExceededError(f"Gemini quota exceeded: {e}")
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            self.status = ProviderStatus.ERROR
            raise ProviderError(f"Gemini error: {e}")
    
    def get_quota_info(self) -> Dict[str, Any]:
        """Get current quota information"""
        config = self.MODEL_CONFIGS.get(self.model_name, {"rpd": 20})
        daily_limit = config['rpd']
        used = self.usage_stats['daily_requests']
        
        # Calculate reset time (midnight UTC)
        now = datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        return {
            'requests_used': used,
            'requests_remaining': max(0, daily_limit - used),
            'daily_limit': daily_limit,
            'reset_time': tomorrow.isoformat(),
            'rpm_limit': config.get('rpm', 0),
            'tpm_limit': config.get('tpm', 0)
        }
    
    def get_model_name(self) -> str:
        """Get the model identifier"""
        return self.model_name
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "gemini"
    
    def get_status(self) -> ProviderStatus:
        """Get current provider status"""
        # Re-check quota
        quota_info = self.get_quota_info()
        if quota_info['requests_remaining'] <= 0:
            self.status = ProviderStatus.QUOTA_EXCEEDED
        elif self.status == ProviderStatus.QUOTA_EXCEEDED and quota_info['requests_remaining'] > 0:
            # Quota has reset
            self.status = ProviderStatus.ACTIVE
            
        return self.status
    
    def supports_search(self) -> bool:
        """Check if search is enabled"""
        return self.enable_search
    
    async def test_connection(self) -> bool:
        """Test if Gemini is accessible"""
        try:
            response = await self.generate("Say 'OK' if you can read this.")
            return len(response) > 0
        except QuotaExceededError:
            # Quota exceeded is still a valid connection
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
