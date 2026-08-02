"""Assessment Plugins package auto-registering built-in plugins."""

from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.assessment.registry import PluginRegistry

# Auto-register reference built-in plugins
_registry = PluginRegistry()
_registry.register(SecurityHeadersPlugin())

__all__ = ["SecurityHeadersPlugin"]
