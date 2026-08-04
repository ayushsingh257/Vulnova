"use client";

import React, { useEffect, useState } from "react";
import { AdminService, UserAdminItem } from "@/services/admin.service";
import { UserManagementTable } from "@/components/settings/user-management-table";
import { InviteUserModal } from "@/components/settings/invite-user-modal";

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
      setUsers(data.users);
    } catch (err: any) {
      setError(err.message || "Failed to load organization users.");
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
    <div className="flex flex-col gap-6 p-6">
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
          className="rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500 transition-all"
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
        <div className="flex h-64 items-center justify-center text-sm text-zinc-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-red-500 border-t-transparent mr-3" />
          <span>Loading Team Members...</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400">
          {error}
        </div>
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
  );
}
