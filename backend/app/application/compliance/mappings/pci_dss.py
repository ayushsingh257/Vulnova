"""PCI DSS 4.0 Compliance Framework Mapping Definition."""

FRAMEWORK_METADATA = {
    "id": "pci_dss",
    "name": "PCI-DSS",
    "version": "PCI DSS 4.0",
    "description": "Payment Card Industry Data Security Standard providing technical and operational requirements designed to protect cardholder data.",
}

CONTROLS = [
    {
        "control_id": "Req-6",
        "title": "Develop and Maintain Secure Systems and Software",
        "description": "Bespoke and custom software must be developed securely to prevent vulnerabilities such as injection, XSS, and broken access controls.",
        "cwes": ["CWE-77", "CWE-79", "CWE-89", "CWE-94", "CWE-502", "CWE-1104"],
        "categories": [
            "Injection",
            "XSS",
            "SQL Injection",
            "Outdated Software",
            "Validation",
        ],
        "remediation_guidance": "Perform continuous security assessments, code reviews, and dependency vulnerability scanning.",
    },
    {
        "control_id": "Req-7",
        "title": "Restrict Access to System Components and Cardholder Data by Business Need to Know",
        "description": "Access to system components and cardholder data must be restricted to authorized personnel based on business need.",
        "cwes": ["CWE-22", "CWE-284", "CWE-285", "CWE-639"],
        "categories": ["Access Control", "IDOR", "Authorization"],
        "remediation_guidance": "Enforce strict role-based access control (RBAC) and least privilege principles across all APIs and data stores.",
    },
    {
        "control_id": "Req-8",
        "title": "Identify Users and Authenticate Access to System Components",
        "description": "Unique user IDs, multi-factor authentication (MFA), and secure password requirements must be enforced.",
        "cwes": ["CWE-287", "CWE-384", "CWE-521", "CWE-613"],
        "categories": ["Authentication", "Session Management"],
        "remediation_guidance": "Mandate MFA for all system access, enforce strong password policies, and rotate authentication credentials.",
    },
    {
        "control_id": "Req-10",
        "title": "Log and Monitor All Access to System Components and Cardholder Data",
        "description": "Audit trails must record all user access, administrative actions, and system events to detect suspicious behavior.",
        "cwes": ["CWE-778"],
        "categories": ["Logging", "Monitoring"],
        "remediation_guidance": "Capture structured JSON audit logs, protect log integrity, and forward logs to centralized SIEM solutions.",
    },
    {
        "control_id": "Req-11",
        "title": "Test Security of System Components and Networks Regularly",
        "description": "Perform internal and external vulnerability scans, penetration testing, and intrusion detection monitoring.",
        "cwes": ["CWE-16", "CWE-200", "CWE-693", "CWE-918"],
        "categories": ["Misconfiguration", "Security Headers", "SSRF", "Configuration"],
        "remediation_guidance": "Schedule automated DAST scanning, perform quarterly vulnerability assessments, and patch critical findings promptly.",
    },
]
