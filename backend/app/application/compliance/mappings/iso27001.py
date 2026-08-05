"""ISO 27001:2022 Compliance Framework Mapping Definition."""

FRAMEWORK_METADATA = {
    "id": "iso27001",
    "name": "ISO 27001",
    "version": "ISO 27001:2022",
    "description": "International standard for information security management systems (ISMS) specifying requirements for establishing, implementing, and continually improving security controls.",
}

CONTROLS = [
    {
        "control_id": "A.5",
        "title": "Organizational Controls",
        "description": "Security policies, roles, responsibilities, and segregation of duties must be defined and enforced across the organization.",
        "cwes": ["CWE-16"],
        "categories": ["Misconfiguration", "Configuration", "Governance"],
        "remediation_guidance": "Document security policies, define explicit role hierarchies, and conduct periodic governance reviews.",
    },
    {
        "control_id": "A.8",
        "title": "Asset Management",
        "description": "Information assets and associated systems must be identified, inventoried, and classified according to risk.",
        "cwes": ["CWE-200", "CWE-311"],
        "categories": ["Asset Management", "Data Protection", "Information Disclosure"],
        "remediation_guidance": "Maintain an automated asset inventory, tag cloud/on-prem targets, and classify data sensitivity.",
    },
    {
        "control_id": "A.9",
        "title": "Access Control",
        "description": "User access rights must be managed, provisioned, and reviewed in alignment with business access control policies.",
        "cwes": ["CWE-22", "CWE-284", "CWE-285", "CWE-287", "CWE-639"],
        "categories": ["Access Control", "IDOR", "Authorization", "Authentication"],
        "remediation_guidance": "Implement role-based access control (RBAC), enforce least privilege, and revoke access upon user departure.",
    },
    {
        "control_id": "A.12",
        "title": "Operations Security",
        "description": "Operational procedures, malware protection, logging, and technical vulnerability management must be operationalized.",
        "cwes": ["CWE-778"],
        "categories": ["Logging", "Monitoring", "Operations Security"],
        "remediation_guidance": "Automate log generation and monitoring, enforce secure backup strategies, and scan for technical vulnerabilities.",
    },
    {
        "control_id": "A.14",
        "title": "System Acquisition, Development and Maintenance",
        "description": "Security must be an integral part of information systems across the entire development lifecycle.",
        "cwes": ["CWE-77", "CWE-79", "CWE-89", "CWE-94", "CWE-502", "CWE-1104"],
        "categories": [
            "Injection",
            "XSS",
            "SQL Injection",
            "Outdated Software",
            "Validation",
        ],
        "remediation_guidance": "Embed security testing (DAST/SAST/SCA) into CI/CD build pipelines and enforce secure coding standards.",
    },
    {
        "control_id": "A.16",
        "title": "Information Security Incident Management",
        "description": "Responsibilities and procedures must be established to ensure quick, effective, and orderly response to security incidents.",
        "cwes": ["CWE-209"],
        "categories": ["Incident Management", "Error Handling", "Logging"],
        "remediation_guidance": "Establish incident response playbooks, define SEV-1 to SEV-4 alert thresholds, and conduct blameless post-incident reviews.",
    },
]
