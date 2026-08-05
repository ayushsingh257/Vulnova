from fastapi import APIRouter

from app.api.v1.routers import (
    admin,
    ai,
    api_keys,
    api_security_validation,
    assessment,
    assets,
    audit_logs,
    auth,
    cli,
    compliance,
    container_validation,
    dashboard,
    discovery,
    infrastructure_validation,
    integrations,
    notifications,
    organizations,
    owasp_validation,
    pentest_validation,
    regression_validation,
    report_exports,
    reports,
    sca_validation,
    scan_schedules,
    scan_stream,
    scan_targets,
    secrets_validation,
    status,
    threat_validation,
    trends,
    triage,
    trust,
    users,
    vulnerabilities,
    workers,
)

api_v1_router = APIRouter()
api_v1_router.include_router(status.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(api_keys.router)

api_v1_router.include_router(users.router)
api_v1_router.include_router(organizations.router)
api_v1_router.include_router(audit_logs.router)
api_v1_router.include_router(discovery.router)
api_v1_router.include_router(assessment.router)
api_v1_router.include_router(scan_stream.router)
api_v1_router.include_router(assets.router)
api_v1_router.include_router(trends.router)
api_v1_router.include_router(triage.router)
api_v1_router.include_router(vulnerabilities.router)
api_v1_router.include_router(ai.router)
api_v1_router.include_router(
    scan_targets.router, prefix="/scan-targets", tags=["Scan Target Management"]
)
api_v1_router.include_router(
    scan_schedules.router, prefix="/scan-schedules", tags=["Scan Schedule Management"]
)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(trust.router)
api_v1_router.include_router(workers.router, prefix="/workers", tags=["Workers"])
api_v1_router.include_router(reports.router)
api_v1_router.include_router(report_exports.router)
api_v1_router.include_router(compliance.router)
api_v1_router.include_router(integrations.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(cli.router)
api_v1_router.include_router(owasp_validation.router)
api_v1_router.include_router(api_security_validation.router)
api_v1_router.include_router(infrastructure_validation.router)
api_v1_router.include_router(pentest_validation.router)
api_v1_router.include_router(sca_validation.router)
api_v1_router.include_router(container_validation.router)
api_v1_router.include_router(secrets_validation.router)
api_v1_router.include_router(threat_validation.router)
api_v1_router.include_router(regression_validation.router)
