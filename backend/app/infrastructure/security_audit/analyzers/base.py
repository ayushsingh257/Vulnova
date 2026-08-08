"""Base Security Analyzer Interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.infrastructure.security_audit.dto import SecurityAuditFindingDTO


class BaseSecurityAnalyzer(ABC):
    """Abstract interface for all specialized domain security analyzers."""

    def __init__(self, category_name: str) -> None:
        self.category_name = category_name

    @abstractmethod
    def run_analysis(
        self, target_context: Optional[Dict[str, Any]] = None
    ) -> List[SecurityAuditFindingDTO]:
        """Execute domain-specific security checks and return findings."""
        pass
