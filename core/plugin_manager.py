"""
Plugin Manager for discovering and loading plugins dynamically.
"""

import os
import importlib
import inspect
import logging
from typing import Dict, List, Type, Any, Optional
from pathlib import Path

from .interfaces import (
    LLMProvider, 
    SearchProvider, 
    ContentStrategy, 
    PlatformConnector,
    PluginLoadError
)

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin discovery, loading, and registration.
    
    Scans the plugins/ directory for valid plugins and provides
    a registry for runtime access.
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        """
        Initialize the plugin manager.
        
        Args:
            plugins_dir: Path to the plugins directory
        """
        self.plugins_dir = Path(plugins_dir)
        self.llm_providers: Dict[str, Type[LLMProvider]] = {}
        self.search_providers: Dict[str, Type[SearchProvider]] = {}
        self.content_strategies: Dict[str, Type[ContentStrategy]] = {}
        self.platform_connectors: Dict[str, Type[PlatformConnector]] = {}
        
    def discover_plugins(self):
        """
        Discover and load all plugins from the plugins directory.
        """
        logger.info(f"Discovering plugins in {self.plugins_dir}")
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory {self.plugins_dir} does not exist. Creating it...")
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            self._create_plugin_structure()
            return
        
        # Discover each plugin type
        self._discover_llm_providers()
        self._discover_search_providers()
        self._discover_content_strategies()
        self._discover_platform_connectors()
        
        logger.info(f"Plugin discovery complete. Found:")
        logger.info(f"  - {len(self.llm_providers)} LLM providers")
        logger.info(f"  - {len(self.search_providers)} Search providers")
        logger.info(f"  - {len(self.content_strategies)} Content strategies")
        logger.info(f"  - {len(self.platform_connectors)} Platform connectors")
    
    def _discover_llm_providers(self):
        """Discover LLM provider plugins"""
        provider_dir = self.plugins_dir / "llm_providers"
        if not provider_dir.exists():
            return
        
        for plugin_file in provider_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                module_name = f"plugins.llm_providers.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find classes that implement LLMProvider
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, LLMProvider) and obj != LLMProvider:
                        plugin_name = getattr(obj, 'PLUGIN_NAME', name.lower())
                        self.llm_providers[plugin_name] = obj
                        logger.info(f"Loaded LLM provider: {plugin_name}")
                        
            except Exception as e:
                logger.error(f"Failed to load LLM provider from {plugin_file}: {e}")
    
    def _discover_search_providers(self):
        """Discover search provider plugins"""
        provider_dir = self.plugins_dir / "search_providers"
        if not provider_dir.exists():
            return
        
        for plugin_file in provider_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                module_name = f"plugins.search_providers.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, SearchProvider) and obj != SearchProvider:
                        plugin_name = getattr(obj, 'PLUGIN_NAME', name.lower())
                        self.search_providers[plugin_name] = obj
                        logger.info(f"Loaded search provider: {plugin_name}")
                        
            except Exception as e:
                logger.error(f"Failed to load search provider from {plugin_file}: {e}")
    
    def _discover_content_strategies(self):
        """Discover content strategy plugins"""
        strategy_dir = self.plugins_dir / "content_strategies"
        if not strategy_dir.exists():
            return
        
        for plugin_file in strategy_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                module_name = f"plugins.content_strategies.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, ContentStrategy) and obj != ContentStrategy:
                        plugin_name = getattr(obj, 'PLUGIN_NAME', name.lower())
                        self.content_strategies[plugin_name] = obj
                        logger.info(f"Loaded content strategy: {plugin_name}")
                        
            except Exception as e:
                logger.error(f"Failed to load content strategy from {plugin_file}: {e}")
    
    def _discover_platform_connectors(self):
        """Discover platform connector plugins"""
        connector_dir = self.plugins_dir / "platform_connectors"
        if not connector_dir.exists():
            return
        
        for plugin_file in connector_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                module_name = f"plugins.platform_connectors.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, PlatformConnector) and obj != PlatformConnector:
                        plugin_name = getattr(obj, 'PLUGIN_NAME', name.lower())
                        self.platform_connectors[plugin_name] = obj
                        logger.info(f"Loaded platform connector: {plugin_name}")
                        
            except Exception as e:
                logger.error(f"Failed to load platform connector from {plugin_file}: {e}")
    
    def _create_plugin_structure(self):
        """Create the plugin directory structure"""
        subdirs = [
            "llm_providers",
            "search_providers",
            "content_strategies",
            "platform_connectors"
        ]
        
        for subdir in subdirs:
            dir_path = self.plugins_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text("# Plugin directory\n")
        
        logger.info("Created plugin directory structure")
    
    def get_llm_provider(self, name: str, **kwargs) -> LLMProvider:
        """
        Instantiate an LLM provider by name.
        
        Args:
            name: Plugin name
            **kwargs: Initialization parameters
            
        Returns:
            LLMProvider instance
            
        Raises:
            PluginLoadError: If plugin not found
        """
        if name not in self.llm_providers:
            raise PluginLoadError(f"LLM provider '{name}' not found")
        
        return self.llm_providers[name](**kwargs)
    
    def get_search_provider(self, name: str, **kwargs) -> SearchProvider:
        """Instantiate a search provider by name"""
        if name not in self.search_providers:
            raise PluginLoadError(f"Search provider '{name}' not found")
        
        return self.search_providers[name](**kwargs)
    
    def get_content_strategy(self, name: str, **kwargs) -> ContentStrategy:
        """Instantiate a content strategy by name"""
        if name not in self.content_strategies:
            raise PluginLoadError(f"Content strategy '{name}' not found")
        
        return self.content_strategies[name](**kwargs)
    
    def get_platform_connector(self, name: str, **kwargs) -> PlatformConnector:
        """Instantiate a platform connector by name"""
        if name not in self.platform_connectors:
            raise PluginLoadError(f"Platform connector '{name}' not found")
        
        return self.platform_connectors[name](**kwargs)
    
    def list_plugins(self) -> Dict[str, List[str]]:
        """
        List all available plugins.
        
        Returns:
            Dictionary with plugin types as keys and plugin names as values
        """
        return {
            'llm_providers': list(self.llm_providers.keys()),
            'search_providers': list(self.search_providers.keys()),
            'content_strategies': list(self.content_strategies.keys()),
            'platform_connectors': list(self.platform_connectors.keys())
        }
