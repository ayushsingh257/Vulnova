"""OWASP ASVS 4.0.3 Compliance Framework Mapping Definition."""

FRAMEWORK_METADATA = {
    "id": "asvs_v4",
    "name": "OWASP ASVS",
    "version": "OWASP ASVS 4.0.3",
    "description": "OWASP Application Security Verification Standard provides a basis for designing, building, and testing technical application security controls.",
}

CONTROLS = [
    {
        "control_id": "V2",
        "title": "Authentication Verification Requirements",
        "description": "Ensure strong user authentication, password controls, multi-factor authentication, and secure credential recovery.",
        "cwes": ["CWE-287", "CWE-384", "CWE-521", "CWE-613"],
        "categories": ["Authentication", "Session Management"],
        "remediation_guidance": "Enforce Argon2id/bcrypt hashing, anti-brute force throttling, and short-lived tokens.",
    },
    {
        "control_id": "V3",
        "title": "Session Management Verification Requirements",
        "description": "Ensure session identifiers are random, protected with Secure/HttpOnly flags, and invalidated upon logout.",
        "cwes": ["CWE-384", "CWE-613", "CWE-614"],
        "categories": ["Session Management", "Authentication"],
        "remediation_guidance": "Set Secure, HttpOnly, and SameSite flags on session cookies and enforce server-side session timeouts.",
    },
    {
        "control_id": "V4",
        "title": "Access Control Verification Requirements",
        "description": "Ensure authorization is enforced at the server side on every request, respecting tenant and object boundaries.",
        "cwes": ["CWE-22", "CWE-284", "CWE-285", "CWE-639"],
        "categories": ["Access Control", "IDOR", "Path Traversal", "Authorization"],
        "remediation_guidance": "Enforce RBAC/ABAC authorization checks on all REST endpoints and validate tenant organization IDs.",
    },
    {
        "control_id": "V5",
        "title": "Validation, Sanitization and Encoding Verification Requirements",
        "description": "Ensure all input is validated against strict schemas and output is encoded according to rendering context.",
        "cwes": ["CWE-77", "CWE-79", "CWE-89", "CWE-94"],
        "categories": ["Validation", "Injection", "XSS", "SQL Injection"],
        "remediation_guidance": "Use parameterization, HTML entity encoding, and input validation schemas.",
    },
    {
        "control_id": "V6",
        "title": "Stored Cryptography Verification Requirements",
        "description": "Ensure secret data at rest is protected with strong cryptographic algorithms and secure key management.",
        "cwes": ["CWE-311", "CWE-327", "CWE-328", "CWE-330"],
        "categories": ["Cryptography", "Data Protection"],
        "remediation_guidance": "Use AES-256-GCM for envelope encryption and store cryptographic keys in secure secret stores.",
    },
    {
        "control_id": "V7",
        "title": "Error Handling and Logging Verification Requirements",
        "description": "Ensure applications do not leak stack traces or internal implementation details and maintain immutable audit trails.",
        "cwes": ["CWE-209", "CWE-778"],
        "categories": ["Error Handling", "Logging", "Information Disclosure"],
        "remediation_guidance": "Sanitize user-facing error messages and record security events into structured append-only audit logs.",
    },
    {
        "control_id": "V8",
        "title": "Data Protection Verification Requirements",
        "description": "Ensure sensitive personal and financial data is handled securely and not cached or exposed unnecessarily.",
        "cwes": ["CWE-200", "CWE-319"],
        "categories": ["Data Protection", "TLS/SSL", "Information Disclosure"],
        "remediation_guidance": "Enforce HTTPS-only communication and apply Cache-Control headers to prevent client-side storage of sensitive data.",
    },
]
