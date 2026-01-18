"""
Shared LLM caller that uses the intelligent API pool.

This ensures ALL agent calls go through the orchestrator's API pool,
which automatically tries Gemma (14.4K RPD) first, then falls back to Gemini.

NO MORE HARDCODED MODEL CALLS!
"""

import logging
from typing import Optional
from core.orchestrator import orchestrator
from core.interfaces import QuotaExceededError, ProviderError

logger = logging.getLogger(__name__)


async def call_llm(prompt: str, max_retries: int = 2) -> str:
    """
    Call LLM using intelligent API pool with automatic model selection.
    
    Flow:
    1. Try gemma-3-4b (14,400 RPD) ← PRIMARY
    2. Try gemma-3-2b (14,400 RPD) ← BACKUP
    3. Try gemma-3-12b (14,400 RPD) ← FALLBACK
    4. Try gemini-2.5-flash-lite (20 RPD)
    5. Try gemini-2.5-flash (20 RPD)
    6. Try gemini-3-flash (20 RPD)
    7. Raise QuotaExceededError if all exhausted
    
    Args:
        prompt: The prompt to send to the LLM
        max_retries: Number of retries on transient errors
        
    Returns:
        Generated text response
        
    Raises:
        QuotaExceededError: If all models have exceeded quota
        ProviderError: If there's a provider error
    """
    # Ensure API pool is set up
    if not orchestrator.api_pool:
        logger.info("Setting up API pool...")
        await orchestrator.setup_api_pool()
    
    # Try calling through the pool
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Calling LLM (attempt {attempt + 1}/{max_retries + 1})")
            response = await orchestrator.api_pool.call(prompt)
            return response
            
        except QuotaExceededError as e:
            # All models exhausted
            logger.error(f"All models quota exceeded: {e}")
            raise
            
        except ProviderError as e:
            # Provider error - retry if attempts remaining
            if attempt < max_retries:
                logger.warning(f"Provider error, retrying: {e}")
                continue
            else:
                logger.error(f"Provider error after {max_retries} retries: {e}")
                raise
                
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error calling LLM: {e}")
            if attempt < max_retries:
                continue
            raise ProviderError(f"LLM call failed: {e}")
    
    # Should never reach here
    raise ProviderError("LLM call failed after all retries")


async def call_llm_simple(prompt: str) -> str:
    """
    Simple LLM call without retry logic.
    Use this for non-critical calls where you want to fail fast.
    
    Args:
        prompt: The prompt to send to the LLM
        
    Returns:
        Generated text response
    """
    if not orchestrator.api_pool:
        await orchestrator.setup_api_pool()
    
    return await orchestrator.api_pool.call(prompt)
