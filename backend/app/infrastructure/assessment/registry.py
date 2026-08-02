"""Plugin Registry managing registration, discovery, and execution of assessment plugins."""

from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.domain.entities.assessment import BaseAssessmentPlugin, PluginMetadata

logger = get_logger("vulnova.plugin_registry")


class PluginRegistry:
    """Singleton registry for security assessment plugins."""

    _instance: Optional["PluginRegistry"] = None
    _plugins: Dict[str, BaseAssessmentPlugin] = {}

    def __new__(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
        return cls._instance

    def register(self, plugin: BaseAssessmentPlugin) -> None:
        """Register a security assessment plugin."""
        plugin_id = plugin.metadata.id
        if plugin_id in self._plugins:
            logger.warning("plugin_registry.overwriting_plugin", plugin_id=plugin_id)
        self._plugins[plugin_id] = plugin
        logger.info(
            "plugin_registry.registered_plugin",
            plugin_id=plugin_id,
            name=plugin.metadata.name,
            version=plugin.metadata.version,
        )

    def get_plugin(self, plugin_id: str) -> Optional[BaseAssessmentPlugin]:
        """Retrieve a registered plugin by ID."""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[PluginMetadata]:
        """List metadata for all registered plugins."""
        return [p.metadata for p in self._plugins.values()]

    def list_plugin_ids(self) -> List[str]:
        """List IDs of all registered plugins."""
        return list(self._plugins.keys())

    def clear(self) -> None:
        """Clear all registered plugins (primarily for test resets)."""
        self._plugins.clear()
