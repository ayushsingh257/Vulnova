"use client";

import React, { useState } from "react";
import { UserAdminItem, AdminService } from "@/services/admin.service";

interface UserManagementTableProps {
  users: UserAdminItem[];
  onUserUpdated: () => void;
}

export const UserManagementTable: React.FC<UserManagementTableProps> = ({
  users,
  onUserUpdated,
}) => {
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const getRoleBadgeClass = (role: string) => {
    switch (role.toUpperCase()) {
      case "OWNER":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "ADMIN":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "SECURITY_ANALYST":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default:
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    setUpdatingId(userId);
    setErrorMessage(null);
    try {
      await AdminService.updateUserRole(userId, newRole);
      onUserUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to update role.");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDeactivate = async (userId: string) => {
    if (!confirm("Are you sure you want to deactivate this account?")) return;
    setUpdatingId(userId);
    setErrorMessage(null);
    try {
      await AdminService.deactivateUser(userId);
      onUserUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to deactivate account.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {errorMessage && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
          {errorMessage}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-zinc-800 bg-zinc-900/50 uppercase tracking-wider text-zinc-400 font-semibold">
            <tr>
              <th className="px-6 py-3">Member</th>
              <th className="px-6 py-3">Role</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">MFA Status</th>
              <th className="px-6 py-3">Created</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-zinc-900/40 transition-all">
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="font-bold text-zinc-100">{user.full_name}</span>
                    <span className="text-zinc-400 font-mono">{user.email}</span>
                  </div>
                </td>

                <td className="px-6 py-4">
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase ${getRoleBadgeClass(
                      user.role
                    )}`}
                  >
                    {user.role}
                  </span>
                </td>

                <td className="px-6 py-4">
                  {user.is_active ? (
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 font-semibold">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-zinc-500 font-semibold">
                      <span className="h-2 w-2 rounded-full bg-zinc-600" />
                      Deactivated
                    </span>
                  )}
                </td>

                <td className="px-6 py-4">
                  {user.is_mfa_enabled ? (
                    <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                      Enrolled
                    </span>
                  ) : (
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
                      Not Enrolled
                    </span>
                  )}
                </td>

                <td className="px-6 py-4 text-zinc-400 font-mono">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>

                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <select
                      value={user.role}
                      disabled={updatingId === user.id}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-200 focus:outline-none"
                    >
                      <option value="VIEWER">VIEWER</option>
                      <option value="SECURITY_ANALYST">SECURITY_ANALYST</option>
                      <option value="ADMIN">ADMIN</option>
                      <option value="OWNER">OWNER</option>
                    </select>

                    {user.is_active && (
                      <button
                        onClick={() => handleDeactivate(user.id)}
                        disabled={updatingId === user.id}
                        className="rounded border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-[10px] font-semibold text-red-400 hover:bg-red-500/20 disabled:opacity-50"
                      >
                        Deactivate
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
