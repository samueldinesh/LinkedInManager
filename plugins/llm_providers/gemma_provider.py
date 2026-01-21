"""
Gemma LLM Provider Plugin for high-volume, basic tasks.

Gemma models have much higher RPD (14,400) compared to Gemini (20),
making them ideal for:
- Text parsing
- Simple generation
- Data extraction
- Non-search tasks
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


class GemmaProvider(LLMProvider):
    """
    Gemma LLM Provider for high-volume tasks.
    
    Verified Supported Models:
    - gemma-3-4b-it (High Quota)
    - gemma-3-12b-it (High Quota)
    - gemma-3-27b-it (High Quota)
    """
    
    PLUGIN_NAME = "gemma"
    
    # Model configurations (Verified from user account)
    # Using 1500 RPD as conservative estimate for Gemma models
    MODEL_CONFIGS = {
        "gemma-3-4b-it": {"rpm": 30, "rpd": 1500, "tpm": 15000, "quality": "basic"},
        "gemma-3-12b-it": {"rpm": 30, "rpd": 1500, "tpm": 15000, "quality": "balanced"},
        "gemma-3-27b-it": {"rpm": 30, "rpd": 1500, "tpm": 15000, "quality": "high"},
    }
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model_name: str = "gemma-3-4b-it",
        temperature: float = 0.7,
        usage_file: str = "data/gemma_usage.json"
    ):
        """
        Initialize Gemma provider.
        
        Args:
            api_key: Google API key
            model_name: Model to use (2b, 4b, or 12b)
            temperature: Generation temperature
            usage_file: Path to usage tracking file
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")  # Uses same key
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY not found")
        
        self.model_name = model_name
        self.temperature = temperature
        self.usage_file = Path(usage_file)
        
        # Ensure data directory exists
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize usage stats
        self.usage_stats = self._load_usage_stats()
        
        # Initialize LangChain model
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=self.api_key,
                temperature=temperature
            )
            self.status = ProviderStatus.ACTIVE
        except Exception as e:
            logger.error(f"Failed to initialize Gemma model: {e}")
            self.status = ProviderStatus.ERROR
            raise ProviderError(f"Failed to initialize Gemma: {e}")
    
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
        Generate text using Gemma.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text
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
            # Call the model
            response = self.llm.invoke(prompt)
            
            # Increment usage
            self._increment_usage()
            
            # Update status
            self.status = ProviderStatus.ACTIVE
            
            return response.content
            
        except google_exceptions.ResourceExhausted as e:
            self.status = ProviderStatus.QUOTA_EXCEEDED
            raise QuotaExceededError(f"Gemma quota exceeded: {e}")
            
        except Exception as e:
            logger.error(f"Gemma generation error: {e}")
            self.status = ProviderStatus.ERROR
            raise ProviderError(f"Gemma error: {e}")
    
    def get_quota_info(self) -> Dict[str, Any]:
        """Get current quota information"""
        config = self.MODEL_CONFIGS.get(self.model_name, {"rpd": 14400})
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
        return "gemma"
    
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
        """Gemma models don't support search grounding currently"""
        return False
    
    async def test_connection(self) -> bool:
        """Test if Gemma is accessible"""
        try:
            response = await self.generate("Say 'OK' if you can read this.")
            return len(response) > 0
        except QuotaExceededError:
            # Quota exceeded is still a valid connection
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
