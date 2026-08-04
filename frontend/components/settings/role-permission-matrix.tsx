"use client";

import React from "react";
import { RolePermissionMatrixResponse } from "@/services/admin.service";

interface RolePermissionMatrixProps {
  matrix: RolePermissionMatrixResponse;
}

export const RolePermissionMatrix: React.FC<RolePermissionMatrixProps> = ({
  matrix,
}) => {
  const roleNames = ["OWNER", "ADMIN", "SECURITY_ANALYST", "VIEWER"];

  return (
    <div className="flex flex-col gap-6">
      {/* Role Definitions Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {matrix.roles.map((r) => (
          <div
            key={r.role_name}
            className="rounded-xl border border-zinc-800 bg-zinc-950 p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold uppercase tracking-wider text-zinc-100">
                {r.role_name}
              </span>
              <span className="rounded bg-zinc-900 px-2 py-0.5 text-[10px] font-mono text-zinc-400">
                Level {r.role_level}
              </span>
            </div>
            <p className="mt-2 text-xs text-zinc-400 leading-relaxed">
              {r.description}
            </p>
            <div className="mt-4 pt-3 border-t border-zinc-800/60">
              <span className="text-[10px] uppercase font-mono text-zinc-500">
                {r.granted_permissions.length} Permissions Granted
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Permission Boundary Matrix Table */}
      <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-zinc-800 bg-zinc-900/50 uppercase tracking-wider text-zinc-400 font-semibold">
            <tr>
              <th className="px-6 py-3">Permission Scope</th>
              <th className="px-6 py-3">Min Role</th>
              {roleNames.map((role) => (
                <th key={role} className="px-6 py-3 text-center">
                  {role}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
            {matrix.permissions.map((p) => {
              return (
                <tr key={p.permission_key} className="hover:bg-zinc-900/40 transition-all">
                  <td className="px-6 py-3">
                    <div className="flex flex-col">
                      <span className="font-mono font-semibold text-zinc-200">
                        {p.permission_key}
                      </span>
                      <span className="text-[10px] text-zinc-400">
                        {p.description}
                      </span>
                    </div>
                  </td>

                  <td className="px-6 py-3">
                    <span className="rounded bg-zinc-900 px-2 py-0.5 text-[10px] font-mono text-zinc-400">
                      {p.minimum_role}
                    </span>
                  </td>

                  {roleNames.map((roleName) => {
                    const roleObj = matrix.roles.find((r) => r.role_name === roleName);
                    const isGranted = roleObj?.granted_permissions.includes(p.permission_key);
                    return (
                      <td key={roleName} className="px-6 py-3 text-center">
                        {isGranted ? (
                          <span className="text-emerald-400 font-bold">✓</span>
                        ) : (
                          <span className="text-zinc-600">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
