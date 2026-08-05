"use client";

import React, { useEffect, useState } from "react";
import { Key, Plus, Trash2, Copy, Check, ShieldAlert, Loader2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CLITokenDTO, CLIService } from "@/services/cli.service";

export const TokenManagementPanel: React.FC = () => {
  const [tokens, setTokens] = useState<CLITokenDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [nameInput, setNameInput] = useState("");
  const [creating, setCreating] = useState(false);
  const [rawToken, setRawToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTokens = async () => {
    setLoading(true);
    try {
      const data = await CLIService.getTokens();
      setTokens(data);
    } catch (err) {
      console.error("Failed to fetch CLI tokens:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  const handleCreateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nameInput.trim()) return;
    setCreating(true);
    try {
      const created = await CLIService.createToken({ name: nameInput });
      if (created.raw_token) {
        setRawToken(created.raw_token);
      }
      setNameInput("");
      fetchTokens();
    } catch (err) {
      console.error("Failed to create CLI token:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string, name: string) => {
    if (!confirm(`Revoke CLI token "${name}"? Pipeline jobs using this token will fail.`)) return;
    try {
      await CLIService.revokeToken(id);
      fetchTokens();
    } catch (err) {
      console.error("Failed to revoke CLI token:", err);
    }
  };

  const handleCopyRaw = () => {
    if (rawToken) {
      navigator.clipboard.writeText(rawToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Key className="h-4 w-4 text-purple-400" />
          <CardTitle className="text-sm font-bold text-white">
            Pipeline API Tokens (vn_cli_)
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4 text-xs">
        {/* Create Token Form */}
        <form onSubmit={handleCreateToken} className="flex items-center space-x-2">
          <input
            type="text"
            required
            placeholder="Token description (e.g. GitHub Actions Release Key)"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            className="flex-1 rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
          />
          <button
            type="submit"
            disabled={creating}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-md bg-purple-600 font-semibold text-white hover:bg-purple-500 transition-colors"
          >
            {creating ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
            )}
            <span>Generate Token</span>
          </button>
        </form>

        {/* Display New Raw Token Warning Box */}
        {rawToken && (
          <div className="p-3 rounded-lg border border-purple-800/60 bg-purple-950/40 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-purple-300">
                New CLI API Token Generated
              </span>
              <button
                onClick={() => setRawToken(null)}
                className="text-zinc-400 hover:text-white"
              >
                Close
              </button>
            </div>
            <p className="text-[11px] text-zinc-400">
              Copy this token now. It will not be shown again.
            </p>
            <div className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded p-2 font-mono text-emerald-400 text-[11px]">
              <code>{rawToken}</code>
              <button
                onClick={handleCopyRaw}
                className="text-zinc-400 hover:text-white p-1"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        )}

        {/* Tokens List */}
        {loading ? (
          <div className="text-center py-4 text-zinc-500">Loading tokens...</div>
        ) : tokens.length === 0 ? (
          <div className="text-center py-4 text-zinc-500">
            No active CLI API tokens. Generate one above.
          </div>
        ) : (
          <div className="space-y-2">
            {tokens.map((tok) => (
              <div
                key={tok.id}
                className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-900/60"
              >
                <div>
                  <span className="font-semibold text-zinc-200 block">
                    {tok.name}
                  </span>
                  <span className="text-[11px] font-mono text-zinc-400">
                    Prefix: {tok.token_prefix}...
                  </span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-[11px] text-zinc-500 font-mono">
                    {tok.last_used_at ? `Used: ${tok.last_used_at.split("T")[0]}` : "Never used"}
                  </span>
                  <button
                    onClick={() => handleRevoke(tok.id, tok.name)}
                    className="p-1 text-zinc-400 hover:text-red-400 transition-colors"
                    title="Revoke Token"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
