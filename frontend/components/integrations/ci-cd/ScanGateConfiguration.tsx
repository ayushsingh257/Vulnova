"use client";

import React, { useState } from "react";
import { ShieldCheck, Sliders, Check } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export const ScanGateConfiguration: React.FC = () => {
  const [maxCritical, setMaxCritical] = useState(0);
  const [maxHigh, setMaxHigh] = useState(2);
  const [maxMedium, setMaxMedium] = useState(10);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Sliders className="h-4 w-4 text-purple-400" />
          <CardTitle className="text-sm font-bold text-white">
            Default Build Security Gate Thresholds
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="pt-4 text-xs">
        <form onSubmit={handleSave} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-zinc-400 font-medium mb-1">Max CRITICAL</label>
              <input
                type="number"
                min="0"
                value={maxCritical}
                onChange={(e) => setMaxCritical(parseInt(e.target.value) || 0)}
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200 font-mono"
              />
            </div>
            <div>
              <label className="block text-zinc-400 font-medium mb-1">Max HIGH</label>
              <input
                type="number"
                min="0"
                value={maxHigh}
                onChange={(e) => setMaxHigh(parseInt(e.target.value) || 0)}
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200 font-mono"
              />
            </div>
            <div>
              <label className="block text-zinc-400 font-medium mb-1">Max MEDIUM</label>
              <input
                type="number"
                min="0"
                value={maxMedium}
                onChange={(e) => setMaxMedium(parseInt(e.target.value) || 0)}
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200 font-mono"
              />
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <p className="text-[11px] text-zinc-500">
              Pipelines will exit with code 1 if findings exceed these limits.
            </p>
            <button
              type="submit"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-purple-600 font-semibold text-white hover:bg-purple-500 transition-colors"
            >
              {saved ? (
                <>
                  <Check className="h-3.5 w-3.5 text-white" />
                  <span>Gate Saved</span>
                </>
              ) : (
                <span>Save Gate Settings</span>
              )}
            </button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
