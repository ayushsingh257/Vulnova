"use client";

import * as React from "react";
import { ShieldCheck, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface ASVSItem {
  category: string;
  title: string;
  description: string;
  status: string;
  asvs_ref?: string;
}

export function ASVSGrid({ items }: { items: ASVSItem[] }) {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">OWASP ASVS v4.0 Control Mappings</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Security Controls Mapped Against OWASP ASVS v4.0
        </span>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-2 hover:border-zinc-700 transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-zinc-200 flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <span>{item.title}</span>
                </span>
                {item.asvs_ref && (
                  <Badge variant="info" className="font-mono text-[10px]">
                    {item.asvs_ref}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">{item.description}</p>
              <div className="pt-2 flex items-center justify-between border-t border-zinc-800/60">
                <span className="text-[10px] font-mono uppercase text-zinc-500">
                  Category: {item.category}
                </span>
                <Badge variant="success" className="text-[9px]">
                  {item.status}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
