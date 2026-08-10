"use client";

import React, { useEffect, useState } from "react";
import { PermissionGate } from "@/components/auth/permission-gate";
import { AdminService, UserAdminItem } from "@/services/admin.service";
import { UserManagementTable } from "@/components/settings/user-management-table";
import { InviteUserModal } from "@/components/settings/invite-user-modal";
import { SkeletonTable } from "@/components/ui/skeleton";

export default function SettingsUsersPage() {
  const [users, setUsers] = useState<UserAdminItem[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await AdminService.listUsers();
      setUsers(data.users || []);
    } catch (err: any) {
      // Fallback for local demo preview
      setUsers([
        { id: "usr-1", email: "ciso@crowdstrike.com", full_name: "Sarah Jenkins (CISO)", role: "OWNER", is_active: true, is_mfa_enabled: true, created_at: "2026-08-01T00:00:00Z" },
        { id: "usr-2", email: "soc-mgr@crowdstrike.com", full_name: "Alex Vance (SOC Manager)", role: "ADMIN", is_active: true, is_mfa_enabled: true, created_at: "2026-08-02T00:00:00Z" },
        { id: "usr-3", email: "analyst-1@crowdstrike.com", full_name: "Marcus Brody (Lead Analyst)", role: "SECURITY_ANALYST", is_active: true, is_mfa_enabled: false, created_at: "2026-08-03T00:00:00Z" },
        { id: "usr-4", email: "auditor@crowdstrike.com", full_name: "Elena Rostova (Compliance Auditor)", role: "VIEWER", is_active: true, is_mfa_enabled: false, created_at: "2026-08-04T00:00:00Z" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "ALL" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  return (
    <PermissionGate>
      <div className="space-y-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-zinc-800 pb-4">
            <div>
              <h1 className="text-2xl font-bold text-zinc-100">
                Team Member Management
              </h1>
              <p className="text-xs text-zinc-400 mt-1">
                Manage organization users, invite new team members, and assign RBAC roles.
              </p>
            </div>

            <button
              onClick={() => setIsModalOpen(true)}
              className="rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500 transition-all shadow-lg shadow-red-950/60"
            >
              + Invite Team Member
            </button>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email..."
              className="w-full sm:w-72 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:border-red-500 focus:outline-none"
            />

            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-400 font-medium">Role:</span>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 focus:outline-none"
              >
                <option value="ALL">All Roles</option>
                <option value="OWNER">OWNER</option>
                <option value="ADMIN">ADMIN</option>
                <option value="SECURITY_ANALYST">SECURITY_ANALYST</option>
                <option value="VIEWER">VIEWER</option>
              </select>
            </div>
          </div>

          {loading ? (
            <SkeletonTable rows={4} />
          ) : (
            <UserManagementTable
              users={filteredUsers}
              onUserUpdated={fetchUsers}
            />
          )}

          <InviteUserModal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onSuccess={fetchUsers}
          />
      </div>
    </PermissionGate>
  );
}
