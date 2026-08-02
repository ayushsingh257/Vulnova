"""Assessment Plugins package auto-registering built-in plugins."""

from app.infrastructure.assessment.plugins.auth_plugin import AuthSecurityPlugin
from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.assessment.plugins.sql_injection_plugin import (
    SQLInjectionPlugin,
)
from app.infrastructure.assessment.plugins.xss_plugin import XSSPlugin
from app.infrastructure.assessment.registry import PluginRegistry

# Auto-register Web Vulnerability Assessment Plugins
_registry = PluginRegistry()
_registry.register(SecurityHeadersPlugin())
_registry.register(SQLInjectionPlugin())
_registry.register(XSSPlugin())
_registry.register(AuthSecurityPlugin())

__all__ = [
    "SecurityHeadersPlugin",
    "SQLInjectionPlugin",
    "XSSPlugin",
    "AuthSecurityPlugin",
]
