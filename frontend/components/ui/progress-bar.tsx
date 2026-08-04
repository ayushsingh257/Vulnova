import * as React from "react";
import { clsx } from "clsx";

export interface ProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0 to 100
  colorVariant?: "crimson" | "blue" | "emerald" | "amber";
}

export function ProgressBar({
  value,
  colorVariant = "crimson",
  className,
  ...props
}: ProgressBarProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100);

  const barColors = {
    crimson: "bg-gradient-to-r from-red-600 to-red-500 shadow-red-500/50",
    blue: "bg-gradient-to-r from-blue-600 to-cyan-500 shadow-cyan-500/50",
    emerald: "bg-gradient-to-r from-emerald-600 to-teal-400 shadow-emerald-500/50",
    amber: "bg-gradient-to-r from-amber-600 to-yellow-400 shadow-amber-500/50",
  };

  return (
    <div
      className={clsx("h-2.5 w-full overflow-hidden rounded-full bg-zinc-800/80 p-0.5", className)}
      {...props}
    >
      <div
        className={clsx(
          "h-full rounded-full transition-all duration-500 ease-out shadow-sm",
          barColors[colorVariant]
        )}
        style={{ width: `${clampedValue}%` }}
      />
    </div>
  );
}
