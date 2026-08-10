"use client";

import React, { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { PermissionGate } from "@/components/auth/permission-gate";
import { AdminService, RolePermissionMatrixResponse } from "@/services/admin.service";
import { RolePermissionMatrix } from "@/components/settings/role-permission-matrix";
import { SkeletonCard } from "@/components/ui/skeleton";

export default function SettingsRolesPage() {
  const [matrix, setMatrix] = useState<RolePermissionMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMatrix() {
      try {
        setLoading(true);
        const data = await AdminService.getRolePermissionMatrix();
        setMatrix(data);
      } catch (err: any) {
        // Fallback demo matrix
        setMatrix({
          roles: [
            { role_name: "OWNER", role_level: 4, description: "Platform Owner", granted_permissions: ["*"] },
            { role_name: "ADMIN", role_level: 3, description: "Organization Admin", granted_permissions: ["users:write", "scans:write"] },
            { role_name: "SECURITY_ANALYST", role_level: 2, description: "SOC Security Analyst", granted_permissions: ["scans:write", "findings:write"] },
            { role_name: "VIEWER", role_level: 1, description: "Read-only Auditor", granted_permissions: ["reports:read"] },
          ],
          permissions: [
            { permission_key: "scans:write", description: "Execute DAST Scans", minimum_role: "SECURITY_ANALYST" },
            { permission_key: "findings:write", description: "Triage & Patch Vulnerabilities", minimum_role: "SECURITY_ANALYST" },
            { permission_key: "users:write", description: "Invite & Manage Team Users", minimum_role: "ADMIN" },
            { permission_key: "admin:access", description: "Platform Control Plane", minimum_role: "OWNER" },
          ],
        });
      } finally {
        setLoading(false);
      }
    }

    loadMatrix();
  }, []);

  return (
    <DashboardLayout>
      <PermissionGate>
        <div className="space-y-6">
          <div className="border-b border-zinc-800 pb-4">
            <h1 className="text-2xl font-bold text-zinc-100">
              RBAC Role & Permission Boundary Matrix
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              Inspect granular resource permission boundaries across OWNER, ADMIN, SECURITY_ANALYST, and VIEWER roles.
            </p>
          </div>

          {loading ? (
            <SkeletonCard />
          ) : matrix ? (
            <RolePermissionMatrix matrix={matrix} />
          ) : null}
        </div>
      </PermissionGate>
    </DashboardLayout>
  );
}
