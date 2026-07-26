"""
Jarvis OS - Plugin Manager

Handles dynamic discovery and loading of custom plugins.
"""

import importlib
import pkgutil
import inspect
from typing import Any
import structlog

from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
import jarvis.plugins

logger = structlog.get_logger(__name__)


class PluginManager:
    """
    Scans the jarvis.plugins namespace and dynamically loads any plugin modules.
    """

    def __init__(self, registry: ToolRegistry, bus: EventBus) -> None:
        self._registry = registry
        self._bus = bus
        self._loaded_plugins: list[str] = []

    def load_all(self) -> None:
        """
        Discover and load all plugins in the jarvis.plugins package.
        """
        logger.info("plugin_manager.scanning")
        
        # Discover all sub-modules in jarvis.plugins
        package = jarvis.plugins
        prefix = package.__name__ + "."
        
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
            if ispkg:
                self.load_plugin(modname)
                
        logger.info("plugin_manager.loaded_all", count=len(self._loaded_plugins))

    def load_plugin(self, module_name: str) -> None:
        """
        Load a specific plugin by its full module name.
        """
        try:
            module = importlib.import_module(module_name)
            
            # Look for a setup() function
            if hasattr(module, "setup") and inspect.isfunction(module.setup):
                # Call the setup function, passing the registry and bus
                module.setup(self._registry, self._bus)
                self._loaded_plugins.append(module_name)
                logger.info("plugin_manager.plugin_loaded", plugin=module_name)
            else:
                logger.warning("plugin_manager.no_setup_found", plugin=module_name)
                
        except Exception as e:
            logger.error("plugin_manager.load_failed", plugin=module_name, error=str(e))
