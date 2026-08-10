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
  ChevronRight,
  Building2,
  Lock,
  Users,
  Shield,
  Eye,
} from "lucide-react";
import { getCurrentUser, setCurrentRole, UserRole, UserProfile } from "@/lib/auth";

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = React.useState<UserProfile>({
    email: "analyst@enterprise-corp.com",
    role: "SECURITY_ANALYST",
    organization: "Acme Corp Enterprise",
    organizationId: "org-acme-001",
    permissions: [],
  });
  const [userDropdownOpen, setUserDropdownOpen] = React.useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    setUser(getCurrentUser());
  }, []);

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

  const handleSwitchRole = (newRole: UserRole) => {
    const updated = setCurrentRole(newRole);
    setUser(updated);
    setUserDropdownOpen(false);
    router.refresh();
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

  // Define full navigation items with role requirements
  const allNavGroups = [
    {
      title: "SOC Operations",
      items: [
        { label: "SOC Dashboard", href: "/dashboard", icon: Activity, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Active Scans", href: "/scans", icon: Radio, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
        { label: "Scan Schedules", href: "/schedules", icon: Calendar, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
        { label: "Notifications", href: "/notifications", icon: Bell, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
      ],
    },
    {
      title: "Security Intelligence & Assets",
      items: [
        { label: "Findings & Vulnerabilities", href: "/findings", icon: ShieldAlert, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Asset Inventory", href: "/assets", icon: Layers, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Executive Reports", href: "/reports", icon: FileText, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Compliance Frameworks", href: "/compliance", icon: ShieldCheck, roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "OWASP Validation", href: "/validation/owasp", icon: ShieldCheck, color: "text-purple-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "API Security", href: "/validation/api-security", icon: Server, color: "text-blue-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Infrastructure Validation", href: "/validation/infrastructure", icon: ShieldCheck, color: "text-emerald-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Penetration Testing", href: "/validation/pentest", icon: ShieldAlert, color: "text-red-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
        { label: "Dependency Security (SCA)", href: "/validation/sca", icon: PackageCheck, color: "text-blue-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Container Security", href: "/validation/container", icon: Boxes, color: "text-cyan-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Secrets Audit", href: "/validation/secrets", icon: KeyRound, color: "text-purple-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Threat Model & STRIDE", href: "/validation/threat", icon: ShieldCheck, color: "text-orange-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Automated Regression", href: "/validation/regression", icon: ShieldAlert, color: "text-teal-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
        { label: "Security Certification", href: "/validation/certification", icon: Award, color: "text-amber-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"] },
      ],
    },
    {
      title: "Admin & Governance",
      items: [
        { label: "Platform Control Plane", href: "/admin", icon: Building2, color: "text-red-400", roles: ["OWNER"] },
        { label: "User Management", href: "/settings/users", icon: Users, color: "text-zinc-300", roles: ["OWNER", "ADMIN"] },
        { label: "Integrations", href: "/integrations", icon: Link2, roles: ["OWNER", "ADMIN"] },
        { label: "Multi-Factor Auth", href: "/security/mfa", icon: KeyRound, color: "text-amber-400", roles: ["OWNER", "ADMIN"] },
        { label: "Evidence Quarantine", href: "/security/quarantine", icon: ShieldAlert, color: "text-cyan-400", roles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
        { label: "Enterprise Secrets Vault", href: "/settings/secrets", icon: KeyRound, color: "text-emerald-400", roles: ["OWNER", "ADMIN"] },
        { label: "Settings", href: "/settings", icon: Settings, roles: ["OWNER", "ADMIN"] },
      ],
    },
  ];

  // Filter navigation items dynamically based on active user role
  const filteredNavGroups = allNavGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => item.roles.includes(user.role)),
    }))
    .filter((group) => group.items.length > 0);

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
              <span className="ml-2 rounded-full border border-red-500/30 bg-red-950/40 px-2 py-0.5 text-[10px] font-semibold text-red-400 font-mono">
                {user.role}
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

          {/* User Profile & Role Switcher Dropdown */}
          <div className="relative border-l border-zinc-800 pl-4" ref={dropdownRef}>
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center space-x-3 p-1 rounded-lg hover:bg-zinc-900 transition-colors focus:outline-none"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-950 border border-red-800/60 text-red-400 font-bold text-xs">
                {user.role.substring(0, 2)}
              </div>
              <div className="hidden md:block text-left text-xs">
                <div className="font-semibold text-zinc-200 flex items-center">
                  <span>{user.email.split("@")[0]}</span>
                  <ChevronDown className="ml-1 h-3 w-3 text-zinc-400" />
                </div>
                <div className="text-[10px] text-zinc-400">{user.organization}</div>
              </div>
            </button>

            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl p-3 z-50 animate-in fade-in slide-in-from-top-2 space-y-3">
                <div className="px-2 py-1.5 border-b border-zinc-800">
                  <p className="text-xs font-semibold text-zinc-200">{user.email}</p>
                  <p className="text-[10px] text-zinc-400 font-mono mt-0.5">{user.organization}</p>
                  <div className="mt-1.5 inline-block px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800/40 text-[10px] font-bold font-mono">
                    ACTIVE ROLE: {user.role}
                  </div>
                </div>

                {/* Role Switcher Demo Tool */}
                <div className="space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 px-2">
                    Switch Role (Local Testing)
                  </p>
                  <div className="grid grid-cols-2 gap-1 text-[11px] font-mono">
                    <button
                      onClick={() => handleSwitchRole("OWNER")}
                      className={`px-2 py-1 rounded text-left transition-colors ${
                        user.role === "OWNER" ? "bg-red-950 text-red-400 font-bold border border-red-800/60" : "hover:bg-zinc-800 text-zinc-300"
                      }`}
                    >
                      👑 OWNER
                    </button>
                    <button
                      onClick={() => handleSwitchRole("ADMIN")}
                      className={`px-2 py-1 rounded text-left transition-colors ${
                        user.role === "ADMIN" ? "bg-red-950 text-red-400 font-bold border border-red-800/60" : "hover:bg-zinc-800 text-zinc-300"
                      }`}
                    >
                      🛡️ ADMIN
                    </button>
                    <button
                      onClick={() => handleSwitchRole("SECURITY_ANALYST")}
                      className={`px-2 py-1 rounded text-left transition-colors ${
                        user.role === "SECURITY_ANALYST" ? "bg-red-950 text-red-400 font-bold border border-red-800/60" : "hover:bg-zinc-800 text-zinc-300"
                      }`}
                    >
                      🔍 ANALYST
                    </button>
                    <button
                      onClick={() => handleSwitchRole("VIEWER")}
                      className={`px-2 py-1 rounded text-left transition-colors ${
                        user.role === "VIEWER" ? "bg-red-950 text-red-400 font-bold border border-red-800/60" : "hover:bg-zinc-800 text-zinc-300"
                      }`}
                    >
                      👁️ VIEWER
                    </button>
                  </div>
                </div>

                <div className="pt-2 border-t border-zinc-800 space-y-1">
                  {user.role === "OWNER" && (
                    <Link
                      href="/admin"
                      onClick={() => setUserDropdownOpen(false)}
                      className="flex items-center space-x-2 px-2 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-950/50 transition-colors font-bold"
                    >
                      <Building2 className="h-4 w-4" />
                      <span>Platform Control Plane</span>
                    </Link>
                  )}
                  <Link
                    href="/settings"
                    onClick={() => setUserDropdownOpen(false)}
                    className="flex items-center space-x-2 px-2 py-1.5 rounded-lg text-xs text-zinc-300 hover:bg-zinc-800 transition-colors"
                  >
                    <Settings className="h-4 w-4 text-zinc-400" />
                    <span>Workspace Settings</span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center space-x-2 px-2 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1">
        {/* Sidebar Navigation (Dynamically Role-Filtered) */}
        <aside
          className={`${
            mobileMenuOpen ? "block" : "hidden"
          } lg:block w-64 flex-col border-r border-zinc-800/80 bg-zinc-950/60 p-4 space-y-6 min-h-[calc(100vh-57px)] shrink-0`}
        >
          {filteredNavGroups.map((group, idx) => (
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
          <span>Vulnova Enterprise Security Platform v1.0.1</span>
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
