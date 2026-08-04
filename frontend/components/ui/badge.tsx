import * as React from "react";
import { clsx } from "clsx";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "critical" | "high" | "medium" | "low" | "info" | "success" | "warning" | "default";
}

export function Badge({ variant = "default", className, ...props }: BadgeProps) {
  const variantStyles = {
    critical: "bg-red-950/80 text-red-400 border-red-800/60 shadow-red-950/50",
    high: "bg-orange-950/80 text-orange-400 border-orange-800/60 shadow-orange-950/50",
    medium: "bg-yellow-950/80 text-yellow-400 border-yellow-800/60 shadow-yellow-950/50",
    low: "bg-blue-950/80 text-blue-400 border-blue-800/60 shadow-blue-950/50",
    info: "bg-zinc-800 text-zinc-300 border-zinc-700",
    success: "bg-emerald-950/80 text-emerald-400 border-emerald-800/60 shadow-emerald-950/50",
    warning: "bg-amber-950/80 text-amber-400 border-amber-800/60 shadow-amber-950/50",
    default: "bg-zinc-800/80 text-zinc-200 border-zinc-700",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:ring-offset-2",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
