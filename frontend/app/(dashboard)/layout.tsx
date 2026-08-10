import * as React from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";

export default function DashboardRouteGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DashboardLayout>{children}</DashboardLayout>;
}
