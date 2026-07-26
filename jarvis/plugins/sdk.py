"""
Jarvis OS — Plugin SDK.

Defines the interface every plugin must implement (spec Volume 8):
  - register()     — called when the plugin is loaded
  - metadata()     — return plugin name, version, description
  - tools()        — return list of Tool instances
  - events()       — return events this plugin subscribes to
  - settings()     — return configurable settings
  - health_check() — return health status

Plugin Lifecycle:
  Discover → Load → Validate → Register → Execute → Unload
"""

from __future__ import annotations

import importlib
import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from jarvis.events.bus import EventHandler, EventBus, get_event_bus
from jarvis.tools.base import Tool

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Plugin metadata
# ---------------------------------------------------------------------------
@dataclass
class PluginMetadata:
    """Descriptive information about a plugin."""

    name: str
    version: str
    description: str
    author: str = ""
    homepage: str = ""
    requires: list[str] = field(default_factory=list)  # dependency plugin names


@dataclass
class PluginHealth:
    """Health status of a plugin."""

    name: str
    healthy: bool
    message: str = ""
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Plugin abstract base
# ---------------------------------------------------------------------------
class Plugin(ABC):
    """
    Abstract base class for all Jarvis plugins.

    Implement at minimum ``metadata()``, ``register()``, and ``tools()``.
    """

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return metadata about this plugin."""
        ...

    @abstractmethod
    async def register(self, bus: EventBus) -> None:
        """
        Called once when the plugin is loaded.

        Use this to subscribe to events, initialise resources, etc.
        """
        ...

    @abstractmethod
    def tools(self) -> list[Tool]:
        """Return the tools this plugin provides."""
        ...

    def events(self) -> dict[str, EventHandler]:
        """Return a mapping of event_type → handler for auto-subscription."""
        return {}

    def settings(self) -> dict[str, Any]:
        """Return configurable settings with defaults."""
        return {}

    async def health_check(self) -> PluginHealth:
        """Check plugin health. Override for custom checks."""
        meta = self.metadata()
        return PluginHealth(name=meta.name, healthy=True, message="OK")

    async def unload(self) -> None:
        """Called when the plugin is being unloaded. Clean up resources."""
        pass


# ---------------------------------------------------------------------------
# Plugin Manager
# ---------------------------------------------------------------------------
class PluginManager:
    """
    Discovers, loads, validates, and manages Jarvis plugins.

    Plugins are Python modules that expose a class inheriting from ``Plugin``.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._bus = get_event_bus()

    # -- Registration -------------------------------------------------------

    async def register_plugin(self, plugin: Plugin) -> None:
        """Register and initialise a single plugin."""
        meta = plugin.metadata()

        # Validate
        if not meta.name:
            raise ValueError("Plugin must have a name")
        if meta.name in self._plugins:
            logger.warning("plugin_manager.duplicate", name=meta.name)
            return

        # Check dependencies
        for dep in meta.requires:
            if dep not in self._plugins:
                raise RuntimeError(
                    f"Plugin '{meta.name}' requires '{dep}', which is not loaded."
                )

        # Register
        await plugin.register(self._bus)

        # Auto-subscribe events
        for event_type, handler in plugin.events().items():
            self._bus.subscribe(event_type, handler)

        self._plugins[meta.name] = plugin
        logger.info(
            "plugin_manager.registered",
            name=meta.name,
            version=meta.version,
            tools=len(plugin.tools()),
        )

    # -- Discovery ----------------------------------------------------------

    async def load_from_directory(self, directory: str | Path) -> int:
        """
        Discover and load plugins from a directory.

        Each plugin should be a Python file or package with a
        ``create_plugin() -> Plugin`` factory function.

        Returns the number of plugins loaded.
        """
        path = Path(directory)
        if not path.exists():
            logger.warning("plugin_manager.directory_not_found", path=str(path))
            return 0

        count = 0
        for item in path.iterdir():
            if item.suffix == ".py" and not item.name.startswith("_"):
                try:
                    plugin = self._load_plugin_file(item)
                    if plugin:
                        await self.register_plugin(plugin)
                        count += 1
                except Exception as exc:
                    logger.error(
                        "plugin_manager.load_error",
                        file=str(item),
                        error=str(exc),
                    )

        logger.info("plugin_manager.loaded", directory=str(path), count=count)
        return count

    def _load_plugin_file(self, filepath: Path) -> Plugin | None:
        """Load a plugin from a Python file."""
        spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        factory = getattr(module, "create_plugin", None)
        if factory is None:
            logger.warning("plugin_manager.no_factory", file=str(filepath))
            return None

        return factory()

    # -- Access -------------------------------------------------------------

    def get(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)

    def list_all(self) -> list[PluginMetadata]:
        """Return metadata for all loaded plugins."""
        return [p.metadata() for p in self._plugins.values()]

    def get_all_tools(self) -> list[Tool]:
        """Return tools from all loaded plugins."""
        tools = []
        for plugin in self._plugins.values():
            tools.extend(plugin.tools())
        return tools

    async def health_check_all(self) -> list[PluginHealth]:
        """Check health of all plugins."""
        results = []
        for plugin in self._plugins.values():
            try:
                health = await plugin.health_check()
                results.append(health)
            except Exception as exc:
                meta = plugin.metadata()
                results.append(PluginHealth(
                    name=meta.name,
                    healthy=False,
                    message=str(exc),
                ))
        return results

    # -- Lifecycle ----------------------------------------------------------

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.unload()
                logger.info("plugin_manager.unloaded", name=name)
            except Exception as exc:
                logger.error("plugin_manager.unload_error", name=name, error=str(exc))
        self._plugins.clear()

    @property
    def count(self) -> int:
        return len(self._plugins)
