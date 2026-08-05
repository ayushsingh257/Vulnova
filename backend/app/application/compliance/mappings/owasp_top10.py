"""OWASP Top 10 2021 Compliance Framework Mapping Definition."""

FRAMEWORK_METADATA = {
    "id": "owasp_top10",
    "name": "OWASP Top 10",
    "version": "OWASP Top 10 2021",
    "description": "Standard awareness document for developers and web application security representing a broad consensus about the most critical security risks.",
}

# Control ID -> Metadata & Matching Criteria (CWE IDs & Categories)
CONTROLS = [
    {
        "control_id": "A01:2021",
        "title": "Broken Access Control",
        "description": "Failures allow unauthorized information disclosure, modification, or destruction of data or performing business functions outside user limits.",
        "cwes": ["CWE-22", "CWE-284", "CWE-285", "CWE-639", "CWE-200"],
        "categories": ["Access Control", "IDOR", "Path Traversal", "Authorization"],
        "remediation_guidance": "Enforce strict server-side access controls, disable directory listing, and minimize CORS usage.",
    },
    {
        "control_id": "A02:2021",
        "title": "Cryptographic Failures",
        "description": "Failures related to cryptography (or lack thereof) leading to exposure of sensitive data or system compromise.",
        "cwes": ["CWE-311", "CWE-319", "CWE-327", "CWE-328", "CWE-330"],
        "categories": ["Cryptography", "TLS/SSL", "Data Protection"],
        "remediation_guidance": "Classify sensitive data, encrypt data in transit with TLS 1.3, and use strong authenticated encryption algorithms.",
    },
    {
        "control_id": "A03:2021",
        "title": "Injection",
        "description": "User-supplied data is not validated, filtered, or sanitized by the application leading to unauthorized command execution.",
        "cwes": ["CWE-77", "CWE-79", "CWE-89", "CWE-94", "CWE-502"],
        "categories": [
            "Injection",
            "XSS",
            "SQL Injection",
            "Command Injection",
            "Cross-Site Scripting",
        ],
        "remediation_guidance": "Use parameterized queries/ORMs, context-aware output encoding, and strict input validation.",
    },
    {
        "control_id": "A04:2021",
        "title": "Insecure Design",
        "description": "Risks related to design and architectural flaws, requiring threat modeling, secure design patterns, and reference architectures.",
        "cwes": ["CWE-209", "CWE-256", "CWE-522"],
        "categories": ["Information Disclosure", "Insecure Design"],
        "remediation_guidance": "Establish secure development lifecycle, use threat modeling, and evaluate plausible threat actors.",
    },
    {
        "control_id": "A05:2021",
        "title": "Security Misconfiguration",
        "description": "Missing security hardening across application stack or improperly configured permissions on cloud services.",
        "cwes": ["CWE-16", "CWE-200", "CWE-693"],
        "categories": ["Misconfiguration", "Security Headers", "Configuration"],
        "remediation_guidance": "Automate hardening, remove unnecessary features/frameworks, and deploy security headers (CSP, HSTS).",
    },
    {
        "control_id": "A06:2021",
        "title": "Vulnerable and Outdated Components",
        "description": "Using software components with known vulnerabilities that weaken application defenses.",
        "cwes": ["CWE-1104"],
        "categories": ["Outdated Software", "SCA", "Third-Party Vulnerability"],
        "remediation_guidance": "Maintain Software Bill of Materials (SBOM), monitor dependencies for CVEs, and update components regularly.",
    },
    {
        "control_id": "A07:2021",
        "title": "Identification and Authentication Failures",
        "description": "Confirmation of the user's identity, authentication, and session management is critical to protect against authentication attacks.",
        "cwes": ["CWE-287", "CWE-384", "CWE-521", "CWE-613"],
        "categories": ["Authentication", "Session Management"],
        "remediation_guidance": "Implement multi-factor authentication (MFA), block weak passwords, and enforce short-lived session tokens.",
    },
    {
        "control_id": "A08:2021",
        "title": "Software and Data Integrity Failures",
        "description": "Code and infrastructure that does not protect against integrity violations, e.g., untrusted updates or CI/CD pipelines.",
        "cwes": ["CWE-502", "CWE-829"],
        "categories": ["Deserialization", "Integrity"],
        "remediation_guidance": "Verify digital signatures on updates/libraries and secure CI/CD build pipelines against unauthorized changes.",
    },
    {
        "control_id": "A09:2021",
        "title": "Security Logging and Monitoring Failures",
        "description": "Insufficient logging and monitoring prevents security teams from detecting active breaches in a timely manner.",
        "cwes": ["CWE-778"],
        "categories": ["Logging", "Monitoring"],
        "remediation_guidance": "Ensure audit logs record high-value transactions and stream logs to SIEM platforms with real-time alerting.",
    },
    {
        "control_id": "A10:2021",
        "title": "Server-Side Request Forgery (SSRF)",
        "description": "Web application fetches remote resources without validating user-supplied URLs, allowing attackers to coerce requests.",
        "cwes": ["CWE-918"],
        "categories": ["SSRF", "Server-Side Request Forgery"],
        "remediation_guidance": "Sanitize and validate user-supplied URL inputs, enforce IP allowlisting, and block network access to cloud IMDS endpoints.",
    },
]
