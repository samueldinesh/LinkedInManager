"""
API Pool Manager for managing multiple LLM providers with quota tracking and failover.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from .interfaces import LLMProvider, ProviderStatus, QuotaExceededError, ProviderError

logger = logging.getLogger(__name__)


class APIPool:
    """
    Manages multiple LLM providers with automatic quota tracking and failover.
    
    Features:
    - Round-robin or priority-based routing
    - Automatic failover when quota exceeded
    - Per-provider quota tracking
    - Health monitoring
    """
    
    def __init__(self, routing_strategy: str = "round_robin"):
        """
        Initialize the API pool.
        
        Args:
            routing_strategy: 'round_robin', 'priority', or 'least_used'
        """
        self.providers: List[LLMProvider] = []
        self.routing_strategy = routing_strategy
        self.current_index = 0
        self._lock = asyncio.Lock()
        self.call_history = defaultdict(int)  # Track calls per provider
        
    def add_provider(self, provider: LLMProvider, priority: int = 0):
        """
        Add a provider to the pool.
        
        Args:
            provider: LLMProvider instance
            priority: Priority level (higher = preferred), used in 'priority' strategy
        """
        self.providers.append({
            'provider': provider,
            'priority': priority,
            'added_at': datetime.utcnow()
        })
        logger.info(f"Added provider: {provider.get_provider_name()} - {provider.get_model_name()}")
        
    def remove_provider(self, provider_name: str, model_name: Optional[str] = None):
        """Remove a provider from the pool"""
        self.providers = [
            p for p in self.providers 
            if not (p['provider'].get_provider_name() == provider_name and 
                   (model_name is None or p['provider'].get_model_name() == model_name))
        ]
        
    async def call(self, prompt: str, **kwargs) -> str:
        """
        Route a generation request to an available provider.
        
        Args:
            prompt: The prompt to generate from
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
            
        Raises:
            ProviderError: If all providers are unavailable
        """
        async with self._lock:
            available_providers = self._get_available_providers()
            
            if not available_providers:
                raise ProviderError("No available providers. All quotas may be exceeded.")
            
            # Try providers in order based on strategy
            for provider_info in available_providers:
                provider = provider_info['provider']
                
                try:
                    logger.info(f"Calling {provider.get_provider_name()} - {provider.get_model_name()}")
                    result = await provider.generate(prompt, **kwargs)
                    
                    # Track successful call
                    provider_key = f"{provider.get_provider_name()}:{provider.get_model_name()}"
                    self.call_history[provider_key] += 1
                    
                    return result
                    
                except QuotaExceededError:
                    logger.warning(f"Quota exceeded for {provider.get_provider_name()}, trying next provider...")
                    continue
                    
                except Exception as e:
                    logger.error(f"Error with provider {provider.get_provider_name()}: {e}")
                    continue
            
            raise ProviderError("All providers failed or quota exceeded")
    
    def _get_available_providers(self) -> List[Dict]:
        """
        Get list of available providers based on routing strategy.
        
        Returns:
            Sorted list of provider info dictionaries
        """
        # Filter out disabled or error providers
        available = [
            p for p in self.providers 
            if p['provider'].get_status() in [ProviderStatus.ACTIVE, ProviderStatus.QUOTA_EXCEEDED]
        ]
        
        if not available:
            return []
        
        # Sort based on strategy
        if self.routing_strategy == "priority":
            available.sort(key=lambda x: x['priority'], reverse=True)
            
        elif self.routing_strategy == "least_used":
            available.sort(
                key=lambda x: self.call_history.get(
                    f"{x['provider'].get_provider_name()}:{x['provider'].get_model_name()}", 
                    0
                )
            )
            
        elif self.routing_strategy == "round_robin":
            # Rotate the list based on current index
            if self.current_index >= len(available):
                self.current_index = 0
            available = available[self.current_index:] + available[:self.current_index]
            self.current_index = (self.current_index + 1) % len(available)
        
        return available
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get status of all providers in the pool.
        
        Returns:
            Dictionary with provider statuses and quota info
        """
        status = {
            'total_providers': len(self.providers),
            'active_providers': 0,
            'providers': []
        }
        
        for provider_info in self.providers:
            provider = provider_info['provider']
            quota_info = provider.get_quota_info()
            
            provider_status = {
                'name': provider.get_provider_name(),
                'model': provider.get_model_name(),
                'status': provider.get_status().value,
                'priority': provider_info['priority'],
                'quota': quota_info,
                'calls_made': self.call_history.get(
                    f"{provider.get_provider_name()}:{provider.get_model_name()}", 
                    0
                )
            }
            
            status['providers'].append(provider_status)
            
            if provider.get_status() == ProviderStatus.ACTIVE:
                status['active_providers'] += 1
        
        return status
    
    async def test_all_providers(self) -> Dict[str, bool]:
        """
        Test connection to all providers.
        
        Returns:
            Dictionary mapping provider names to connection status
        """
        results = {}
        
        for provider_info in self.providers:
            provider = provider_info['provider']
            provider_key = f"{provider.get_provider_name()}:{provider.get_model_name()}"
            
            try:
                results[provider_key] = await provider.test_connection()
            except Exception as e:
                logger.error(f"Connection test failed for {provider_key}: {e}")
                results[provider_key] = False
        
        return results
    
    def get_total_daily_capacity(self) -> int:
        """
        Calculate total daily request capacity across all providers.
        
        Returns:
            Total number of requests available per day
        """
        total = 0
        for provider_info in self.providers:
            quota_info = provider_info['provider'].get_quota_info()
            total += quota_info.get('daily_limit', 0)
        
        return total
