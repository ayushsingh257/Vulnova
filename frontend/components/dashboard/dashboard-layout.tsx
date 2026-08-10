"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldAlert,
  ShieldCheck,
  Award,
  Link2,
  Bell,
  Activity,
  Calendar,
  Layers,
  FileText,
  Settings,
  User,
  Radio,
  Search,
  Server,
  PackageCheck,
  Boxes,
  KeyRound,
  Database,
  LogOut,
  ChevronDown,
  Menu,
  X,
  Home,
  ChevronRight,
} from "lucide-react";

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [userDropdownOpen, setUserDropdownOpen] = React.useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
    }
    setUserDropdownOpen(false);
    router.push("/login");
  };

  const isActive = (path: string) => {
    if (path === "/dashboard" && pathname === "/dashboard") return true;
    if (path !== "/dashboard" && pathname?.startsWith(path)) return true;
    return false;
  };

  // Breadcrumb generator
  const getBreadcrumbs = () => {
    if (!pathname) return [{ label: "Dashboard", href: "/dashboard" }];
    const segments = pathname.split("/").filter(Boolean);
    const crumbs = [{ label: "Home", href: "/" }];
    
    let currentPath = "";
    segments.forEach((seg) => {
      currentPath += `/${seg}`;
      const formatted = seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, " ");
      crumbs.push({ label: formatted, href: currentPath });
    });
    return crumbs;
  };

  const navGroups = [
    {
      title: "Operations Control",
      items: [
        { label: "SOC Dashboard", href: "/dashboard", icon: Activity },
        { label: "Active Scans", href: "/scans", icon: Radio },
        { label: "Scan Schedules", href: "/schedules", icon: Calendar },
        { label: "Integrations", href: "/integrations", icon: Link2 },
        { label: "Notifications", href: "/notifications", icon: Bell },
      ],
    },
    {
      title: "Intelligence & Assets",
      items: [
        { label: "Vulnerabilities", href: "/findings", icon: ShieldAlert },
        { label: "Asset Inventory", href: "/assets", icon: Layers },
        { label: "Executive Reports", href: "/reports", icon: FileText },
        { label: "Compliance Frameworks", href: "/compliance", icon: ShieldCheck },
        { label: "OWASP Validation", href: "/validation/owasp", icon: ShieldCheck, color: "text-purple-400" },
        { label: "API Security Validation", href: "/validation/api-security", icon: Server, color: "text-blue-400" },
        { label: "Infrastructure Validation", href: "/validation/infrastructure", icon: ShieldCheck, color: "text-emerald-400" },
        { label: "Penetration Testing", href: "/validation/pentest", icon: ShieldAlert, color: "text-red-400" },
        { label: "Dependency Security (SCA)", href: "/validation/sca", icon: PackageCheck, color: "text-blue-400" },
        { label: "Container Security", href: "/validation/container", icon: Boxes, color: "text-cyan-400" },
        { label: "Secrets & Cryptography", href: "/validation/secrets", icon: KeyRound, color: "text-purple-400" },
        { label: "Threat Model & STRIDE", href: "/validation/threat", icon: ShieldCheck, color: "text-orange-400" },
        { label: "Automated Regression", href: "/validation/regression", icon: ShieldAlert, color: "text-teal-400" },
        { label: "Security Certification", href: "/validation/certification", icon: Award, color: "text-amber-400" },
      ],
    },
    {
      title: "Admin & Infrastructure",
      items: [
        { label: "Database Performance", href: "/database/performance", icon: Database, color: "text-cyan-400" },
        { label: "Multi-Factor Auth", href: "/security/mfa", icon: KeyRound, color: "text-amber-400" },
        { label: "Evidence Quarantine", href: "/security/quarantine", icon: ShieldAlert, color: "text-cyan-400" },
        { label: "Enterprise Secrets Vault", href: "/settings/secrets", icon: KeyRound, color: "text-emerald-400" },
        { label: "Settings", href: "/settings", icon: Settings },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-red-500/30 flex flex-col">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-xl px-4 lg:px-6 py-3 flex items-center justify-between shadow-2xl">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 text-zinc-400 hover:text-white"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-600/20 border border-red-500/40 text-red-500 shadow-md shadow-red-950/50 transition-transform group-hover:scale-105">
              <ShieldAlert className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <span className="text-lg font-extrabold tracking-wider text-white">VULNOVA</span>
              <span className="ml-2 rounded-full border border-red-500/30 bg-red-950/40 px-2 py-0.5 text-[10px] font-semibold text-red-400">
                SOC ENTERPRISE
              </span>
            </div>
          </Link>

          <div className="hidden md:flex items-center space-x-2 border-l border-zinc-800 pl-4">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Search targets, findings, CVEs..."
                className="h-9 w-64 rounded-md border border-zinc-800 bg-zinc-900/60 pl-9 pr-4 text-xs text-zinc-200 placeholder-zinc-500 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1 text-xs text-emerald-400">
            <Radio className="h-3.5 w-3.5 animate-ping text-emerald-500" />
            <span className="font-mono text-[11px]">WEBSOCKET STREAM ACTIVE</span>
          </div>

          <Link href="/notifications" className="relative p-2 text-zinc-400 hover:text-white transition-colors">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-zinc-950" />
          </Link>

          {/* User Profile Dropdown Menu */}
          <div className="relative border-l border-zinc-800 pl-4" ref={dropdownRef}>
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center space-x-3 p-1 rounded-lg hover:bg-zinc-900 transition-colors focus:outline-none"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300 font-bold text-xs">
                SA
              </div>
              <div className="hidden md:block text-left text-xs">
                <div className="font-semibold text-zinc-200 flex items-center">
                  <span>Security Analyst</span>
                  <ChevronDown className="ml-1 h-3 w-3 text-zinc-400" />
                </div>
                <div className="text-[10px] text-zinc-400">Acme Corp Enterprise</div>
              </div>
            </button>

            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl p-2 z-50 animate-in fade-in slide-in-from-top-2">
                <div className="px-3 py-2 border-b border-zinc-800 mb-1">
                  <p className="text-xs font-semibold text-zinc-200">Security Analyst</p>
                  <p className="text-[11px] text-zinc-400 font-mono">analyst@acme-corp.com</p>
                  <span className="inline-block mt-1 px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800/40 text-[10px] font-bold">
                    ROLE: ADMIN
                  </span>
                </div>
                <Link
                  href="/settings/organization"
                  onClick={() => setUserDropdownOpen(false)}
                  className="flex items-center space-x-2 px-3 py-2 rounded-lg text-xs text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  <User className="h-4 w-4 text-zinc-400" />
                  <span>Profile & Account</span>
                </Link>
                <Link
                  href="/settings"
                  onClick={() => setUserDropdownOpen(false)}
                  className="flex items-center space-x-2 px-3 py-2 rounded-lg text-xs text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  <Settings className="h-4 w-4 text-zinc-400" />
                  <span>Enterprise Settings</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-xs text-red-400 hover:bg-red-950/50 transition-colors border-t border-zinc-800 mt-1"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1">
        {/* Sidebar Navigation (Desktop & Mobile) */}
        <aside
          className={`${
            mobileMenuOpen ? "block" : "hidden"
          } lg:block w-64 flex-col border-r border-zinc-800/80 bg-zinc-950/60 p-4 space-y-6 min-h-[calc(100vh-57px)] shrink-0`}
        >
          {navGroups.map((group, idx) => (
            <div key={idx} className="space-y-1">
              <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
                {group.title}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center space-x-3 rounded-lg px-3 py-2 text-xs transition-colors ${
                      active
                        ? "bg-red-950/60 border border-red-800/50 text-red-400 font-bold shadow-sm"
                        : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 font-medium"
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${item.color || ""}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </aside>

        {/* Main Content Workspace */}
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto max-w-7xl mx-auto space-y-6 w-full">
          {/* Breadcrumb Trail */}
          <nav className="flex items-center space-x-2 text-xs text-zinc-500 font-mono pb-2 border-b border-zinc-800/40">
            {getBreadcrumbs().map((crumb, idx) => (
              <React.Fragment key={crumb.href}>
                {idx > 0 && <ChevronRight className="h-3 w-3 text-zinc-600" />}
                <Link
                  href={crumb.href}
                  className={`hover:text-zinc-200 transition-colors ${
                    idx === getBreadcrumbs().length - 1 ? "text-zinc-300 font-bold" : ""
                  }`}
                >
                  {crumb.label}
                </Link>
              </React.Fragment>
            ))}
          </nav>

          {children}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-zinc-800/80 bg-zinc-950/80 px-6 py-4 text-center text-xs text-zinc-500 flex flex-col sm:flex-row items-center justify-between gap-4 mt-auto">
        <div className="flex items-center space-x-2">
          <span>Vulnova Enterprise Security Platform v1.0.0</span>
          <span className="text-zinc-700">•</span>
          <span className="text-emerald-500 font-mono">SOC 2 TYPE II CERTIFIED</span>
        </div>
        <div className="flex items-center space-x-4">
          <Link href="/trust" className="hover:text-zinc-300 transition-colors">
            Trust Center
          </Link>
          <Link href="/security" className="hover:text-zinc-300 transition-colors">
            Vulnerability Disclosure
          </Link>
          <a
            href="/.well-known/security.txt"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-zinc-300 transition-colors font-mono"
          >
            security.txt
          </a>
        </div>
      </footer>
    </div>
  );
}
