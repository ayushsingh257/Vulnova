import * as React from "react";
import type { Metadata } from "next";
import { TrustHeader } from "@/components/trust/trust-header";
import { ASVSGrid } from "@/components/trust/asvs-grid";
import { EncryptionCard } from "@/components/trust/encryption-card";
import { SecurityDisclosureCard } from "@/components/trust/security-disclosure-card";

export const metadata: Metadata = {
  title: "Enterprise Trust Center & Security Posture | Vulnova",
  description:
    "Explore Vulnova's enterprise security architecture disclosures, OWASP ASVS v4.0 control mappings, container sandbox boundaries, and AES-256-GCM encryption specifications.",
  openGraph: {
    title: "Vulnova Enterprise Trust Center",
    description: "OWASP ASVS v4.0 Control Mappings & Container Sandbox Isolation Architecture",
    url: "https://vulnova.com/trust",
    siteName: "Vulnova Security",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Vulnova Enterprise Trust Center",
    description: "OWASP ASVS v4.0 Control Mappings & Container Sandbox Isolation Architecture",
  },
};

const defaultASVSItems = [
  {
    category: "V17_WORKER_SANDBOX",
    title: "Container Sandbox Worker Isolation",
    description:
      "Scanner execution workers run inside unprivileged Linux containers with UID 10001, read-only rootfs, dropped capabilities, and strict egress proxy controls.",
    status: "ENFORCED",
    asvs_ref: "V14.2.1",
  },
  {
    category: "V6_CRYPTOGRAPHY",
    title: "Envelope Data Encryption at Rest",
    description:
      "Target contracts, scan configurations, and finding evidence are encrypted using AES-256-GCM envelope encryption with KMS key rotation.",
    status: "ENFORCED",
    asvs_ref: "V6.2.1",
  },
  {
    category: "V4_ACCESS_CONTROL",
    title: "Multi-Tenant Boundary Isolation",
    description:
      "Every SQL aggregation and cache access query strictly enforces tenant organization scoping, preventing cross-tenant data leakage.",
    status: "ENFORCED",
    asvs_ref: "V4.1.1",
  },
  {
    category: "V2_AUTHENTICATION",
    title: "Authorized Assessment Contract Enforcement",
    description:
      "Mandatory target authorization consent workflow blocks scan dispatch against unverified domains, preventing unauthorized scanning.",
    status: "ENFORCED",
    asvs_ref: "V2.1.2",
  },
  {
    category: "V5_VALIDATION_SANITIZATION",
    title: "Input Schema & Output Payload Sanitization",
    description:
      "Strict Pydantic v2 validation enforces type bounds on API boundaries; sensitive headers/cookies are masked before event stream emission.",
    status: "ENFORCED",
    asvs_ref: "V5.1.1",
  },
  {
    category: "V3_SESSION_MANAGEMENT",
    title: "Short-Lived JWT & API Key Scoping",
    description:
      "Analyst sessions use RS256 signed JWTs with 15-minute access token expiry and Argon2id hashed API keys.",
    status: "ENFORCED",
    asvs_ref: "V3.2.1",
  },
];

export default function TrustCenterPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-red-500/30">
      <TrustHeader />

      <main className="max-w-7xl mx-auto px-6 py-12 space-y-10">
        {/* Hero Banner */}
        <section className="text-center space-y-4 max-w-3xl mx-auto">
          <div className="inline-flex items-center space-x-2 rounded-full border border-red-500/30 bg-red-950/40 px-3 py-1 text-xs text-red-400 font-mono">
            <span>ENTERPRISE SECURITY & COMPLIANCE GATEWAY</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white">
            Trust & Security Architecture
          </h1>
          <p className="text-sm md:text-base text-zinc-400 leading-relaxed">
            Transparent security disclosures, container sandbox isolation specifications, encryption controls,
            and OWASP ASVS v4.0 security control mappings for Vulnova Enterprise.
          </p>
        </section>

        {/* Section 1: ASVS Mappings */}
        <ASVSGrid items={defaultASVSItems} />

        {/* Section 2: Cryptographic & Container Sandbox Boundaries */}
        <EncryptionCard />

        {/* Section 3: Vulnerability Disclosure Policy */}
        <SecurityDisclosureCard />
      </main>
    </div>
  );
}
