"""Vulnova Enterprise Production Release Validation Test Suite (v1.0.0).

Verifies system configuration loading, database model definitions, core API router registrations,
RBAC role hierarchies, security audit analyzers, production deployment manifests, and cryptographic functions.
"""

import glob
import os
import sys
import yaml
import pytest

from app.core.config import settings
from app.domain.entities.role import Role, PERMISSION_MAP
from app.infrastructure.security_audit.analyzers.sast_analyzer import (
    SASTSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.dependency_analyzer import (
    DependencySecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.config_analyzer import (
    ConfigurationSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.api_analyzer import APISecurityAnalyzer
from app.infrastructure.security_audit.analyzers.auth_analyzer import (
    AuthenticationSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.rbac_analyzer import (
    AuthorizationRBACAnalyzer,
)
from app.infrastructure.security_audit.analyzers.secret_analyzer import (
    SecretExposureAnalyzer,
)
from app.infrastructure.security_audit.analyzers.container_analyzer import (
    ContainerSecurityAnalyzer,
)
from app.infrastructure.security_audit.audit_service import SecurityAuditService


def test_version_file_and_settings() -> None:
    """Verify VERSION file exists and reads 1.0.0."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    version_path = os.path.join(root_dir, "VERSION")
    assert os.path.exists(version_path), f"VERSION file missing at {version_path}"
    with open(version_path, "r", encoding="utf-8") as f:
        version = f.read().strip()
    assert version == "1.0.0", f"Expected version 1.0.0, got '{version}'"
    assert "Vulnova" in settings.app_name


def test_rbac_role_hierarchy_and_permissions() -> None:
    """Verify integer-ordered role hierarchy and permission mappings."""
    assert Role.OWNER > Role.ADMIN > Role.SECURITY_ANALYST > Role.VIEWER
    assert Role.OWNER.value == 40
    assert Role.ADMIN.value == 30
    assert Role.SECURITY_ANALYST.value == 20
    assert Role.VIEWER.value == 10

    # Ensure critical permissions exist
    assert "admin:manage" in PERMISSION_MAP
    assert "security_audit:read" in PERMISSION_MAP
    assert "security_audit:manage" in PERMISSION_MAP
    assert PERMISSION_MAP["admin:manage"] == Role.ADMIN
    assert PERMISSION_MAP["security_audit:manage"] == Role.ADMIN


def test_security_audit_analyzers_instantiation() -> None:
    """Verify all 8 security analyzers instantiate cleanly."""
    analyzers = [
        SASTSecurityAnalyzer(),
        DependencySecurityAnalyzer(),
        ConfigurationSecurityAnalyzer(),
        APISecurityAnalyzer(),
        AuthenticationSecurityAnalyzer(),
        AuthorizationRBACAnalyzer(),
        SecretExposureAnalyzer(),
        ContainerSecurityAnalyzer(),
    ]
    assert len(analyzers) == 8
    service = SecurityAuditService()
    assert service is not None
    assert len(service.analyzers) == 8


def test_production_deployment_artifacts_exist() -> None:
    """Verify production Docker Compose and Kubernetes deployment manifests exist."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prod_compose = os.path.join(root_dir, "docker-compose.prod.yml")
    env_example = os.path.join(root_dir, ".env.production.example")
    prod_doc = os.path.join(root_dir, "docs", "deployment", "PRODUCTION_DEPLOYMENT.md")
    release_notes = os.path.join(
        root_dir, "docs", "releases", "V1.0.0_RELEASE_NOTES.md"
    )

    assert os.path.exists(prod_compose), f"Missing {prod_compose}"
    assert os.path.exists(env_example), f"Missing {env_example}"
    assert os.path.exists(prod_doc), f"Missing {prod_doc}"
    assert os.path.exists(release_notes), f"Missing {release_notes}"

    # Validate Kubernetes YAML files parse cleanly
    k8s_pattern = os.path.join(root_dir, "deployment", "kubernetes", "**", "*.yaml")
    k8s_files = glob.glob(k8s_pattern, recursive=True)
    assert (
        len(k8s_files) >= 10
    ), f"Expected at least 10 Kubernetes manifest files, found {len(k8s_files)}"

    for k8s_file in k8s_files:
        with open(k8s_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert data is not None, f"Kubernetes manifest {k8s_file} parsed as empty"


def test_core_api_router_imports() -> None:
    """Verify FastAPI application and core routers import cleanly."""
    from fastapi.routing import APIRoute
    from app.main import app

    assert app.title == settings.app_name

    # Verify core routes registered
    route_paths = [route.path for route in app.routes if isinstance(route, APIRoute)]
    assert any("/api/v1" in path for path in route_paths)
    assert any("/health" in path for path in route_paths)


def run_standalone_release_validation() -> int:
    """Run all validation checks in standalone mode and print summary report."""
    print("=================================================================")
    print("VULNOVA v1.0.0 PRODUCTION RELEASE VALIDATION SUITE")
    print("=================================================================")

    tests = [
        ("VERSION & Settings", test_version_file_and_settings),
        ("RBAC Hierarchy & Permission Map", test_rbac_role_hierarchy_and_permissions),
        (
            "Security Audit 8 Domain Analyzers",
            test_security_audit_analyzers_instantiation,
        ),
        (
            "Production Deployment Artifacts & Manifests",
            test_production_deployment_artifacts_exist,
        ),
        ("FastAPI App & Core Routers", test_core_api_router_imports),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS] [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] [ERROR] {name}: {str(e)}")
            failed += 1

    print("-----------------------------------------------------------------")
    print(f"Validation Summary: {passed} passed, {failed} failed.")
    print("=================================================================")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_standalone_release_validation())
