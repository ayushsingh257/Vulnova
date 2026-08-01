# Vulnova — Frontend Design System & Engineering Guidelines (FRONTEND_GUIDELINES.md)

This document establishes the UI design system guidelines, color token architecture, component patterns, state management rules, Enterprise Trust Center public page specifications, and accessibility standards for the **Next.js 14** web application.

---

## 🎨 1. Design System & Brand Aesthetics

Vulnova's frontend is designed to feel like a high-end enterprise SaaS platform (comparable to CrowdStrike, SentinelOne, Snyk). It avoids template aesthetics in favor of a custom, obsidian-and-crimson cybersecurity visual identity.

### A. Core Color Tokens

#### Light Theme (White & Crimson Red)
- `bg-primary`: `#FFFFFF` (Pure Crisp White)
- `bg-secondary`: `#F8FAFC` (Slate Tint Container)
- `border-subtle`: `#E2E8F0` (Subtle Slate Divider)
- `text-primary`: `#0F172A` (Deep Slate Obsidian)
- `text-muted`: `#64748B` (Muted Secondary Text)
- `accent-crimson`: `#DC2626` (Vibrant Crimson Red)
- `accent-hover`: `#B91C1C` (Dark Crimson Hover)

#### Dark Theme (Obsidian Black & Crimson Red)
- `bg-primary`: `#09090B` (Deep Obsidian Black)
- `bg-secondary`: `#18181B` (Zinc Dark Container)
- `border-subtle`: `#27272A` (Zinc Boundary Line)
- `text-primary`: `#FAFAFA` (Crisp Bright White)
- `text-muted`: `#A1A1AA` (Zinc Muted Text)
- `accent-crimson`: `#EF4444` (Glowing Crimson Red)
- `accent-glow`: `rgba(239, 68, 68, 0.25)` (Crimson Glow Box Shadow)

---

## 🛡️ 2. Enterprise Trust Center (`/trust`) Public Page Specification

The **Trust Center** page (`frontend/app/(public)/trust/page.tsx`) provides transparent visibility into Vulnova's enterprise security posture, compliance readiness, data privacy controls, and operational health.

### Key Visual Sections:
1. **Security Posture & Compliance Grid**: Interactive cards displaying SOC 2 Type II readiness, ISO 27001 mapping, OWASP ASVS v4.0 verification badge, and GDPR compliance stance.
2. **Encryption & Data Isolation Disclosures**: Technical explanations of AES-256-GCM data encryption at rest, TLS 1.3 in transit, and multi-tenant row-level DB isolation.
3. **Scanner Sandbox & Safety Controls**: Documentation of scanner container sandbox isolation, egress proxy filtering, and legal target ownership verification policy.
4. **Real-time Platform Operational Status**: Live system status health indicator widget (API Gateway, Scanner Queue, AI Analyst Engine).
5. **Security Document Download Center**: Downloadable whitepapers, security architecture overview PDF, and penetration audit summary reports.

---

## 🧩 3. Component Hierarchy & `shadcn/ui` Extensions

UI components follow strict modularity. They reside in `frontend/components/`:

- `components/ui/`: Low-level atomic components (`button.tsx`, `dialog.tsx`, `table.tsx`, `badge.tsx`, `input.tsx`).
- `components/dashboard/`: Contextual enterprise widgets (`risk-score-card.tsx`, `scan-progress-bar.tsx`, `finding-triage-drawer.tsx`).
- `components/trust/`: Trust Center components (`compliance-badge-card.tsx`, `system-status-indicator.tsx`).
- `components/ai/`: AI Analyst components (`ai-remediation-patch.tsx`, `attack-tree-graph.tsx`).

---

## ⚡ 4. UI State Management & Data Fetching

1. **Server Components First**: Use Next.js React Server Components (RSC) for initial page loads and static data fetching.
2. **TanStack Query (React Query)**: Client-side dynamic state, caching, polling, and optimistic UI mutations for findings and scan profiles.
3. **WebSocket Context (`useScanWebSocket`)**: React Context provider managing persistent WebSocket connection for live scan progress streaming.

---

## 🎭 5. Motion & Micro-Animations (Framer Motion)

- **Hover States**: Subtle scale transitions (`scale: 1.02`) on action cards and severity badges.
- **Page Transitions**: Smooth fade-in (`opacity: 0` to `opacity: 1`) on page routing.
- **Live Scanners**: Pulsing red status indicators (`animate-pulse`) for active DAST scanning states.

---

## ♿ 6. Accessibility & SEO Standards

- **WAI-ARIA**: All interactive elements (modal dialogs, dropdowns, popovers) must pass keyboard navigation and screen reader audits.
- **Semantic HTML5**: Structural page markup utilizes `<main>`, `<nav>`, `<aside>`, `<header>`, and `<footer>`.
- **Unique Component IDs**: Every button, input field, and interactive control carries a unique `id` attribute to support Playwright automated E2E testing.
