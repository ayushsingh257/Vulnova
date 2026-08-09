"use client";

import React, { useState, useCallback } from "react";
import {
  AIConfidenceService,
  FindingConfidenceResult,
  FindingVerificationAttempt,
  FindingReview,
  ReviewDecision,
} from "@/services/ai_confidence.service";

interface FindingConfidencePanelProps {
  findingId: string;
}

const confidenceLevelConfig: Record<
  string,
  { color: string; bg: string; border: string; icon: string }
> = {
  CONFIRMED: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    icon: "✓",
  },
  HIGH: {
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    icon: "▲",
  },
  MEDIUM: {
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    icon: "●",
  },
  LOW: {
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    border: "border-zinc-500/30",
    icon: "▽",
  },
};

const verificationStatusColors: Record<string, string> = {
  CONFIRMED: "text-emerald-400",
  FALSE_POSITIVE: "text-red-400",
  VERIFYING: "text-amber-400",
  NEEDS_REVIEW: "text-yellow-400",
  UNVERIFIED: "text-zinc-400",
};

export const FindingConfidencePanel: React.FC<FindingConfidencePanelProps> = ({
  findingId,
}) => {
  const [confidence, setConfidence] = useState<FindingConfidenceResult | null>(
    null
  );
  const [verification, setVerification] =
    useState<FindingVerificationAttempt | null>(null);
  const [review, setReview] = useState<FindingReview | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchConfidence = useCallback(async () => {
    setLoading("confidence");
    setError(null);
    try {
      const result = await AIConfidenceService.getConfidence(findingId);
      setConfidence(result);
    } catch (err: any) {
      setError(err.message || "Failed to calculate confidence");
    } finally {
      setLoading(null);
    }
  }, [findingId]);

  const triggerVerification = useCallback(async () => {
    setLoading("verify");
    setError(null);
    try {
      const result = await AIConfidenceService.verifyFinding(findingId);
      setVerification(result);
      // Refresh confidence after verification
      const conf = await AIConfidenceService.getConfidence(findingId);
      setConfidence(conf);
    } catch (err: any) {
      setError(err.message || "Verification failed");
    } finally {
      setLoading(null);
    }
  }, [findingId]);

  const submitReview = useCallback(
    async (decision: ReviewDecision) => {
      setLoading("review");
      setError(null);
      try {
        const result = await AIConfidenceService.reviewFinding(
          findingId,
          decision,
          `Analyst decision: ${decision}`
        );
        setReview(result);
      } catch (err: any) {
        setError(err.message || "Review submission failed");
      } finally {
        setLoading(null);
      }
    },
    [findingId]
  );

  const levelConfig =
    confidenceLevelConfig[confidence?.confidence_level || "LOW"];

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-zinc-100">
          AI Confidence Intelligence
        </h3>
        <button
          onClick={fetchConfidence}
          disabled={loading !== null}
          className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-500/20 transition-colors disabled:opacity-50"
        >
          {loading === "confidence" ? "Calculating…" : "Calculate Confidence"}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {confidence && (
        <div className="space-y-4">
          {/* Confidence Score Header */}
          <div
            className={`rounded-xl border ${levelConfig.border} ${levelConfig.bg} p-5`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Confidence Score
                </p>
                <p className={`text-4xl font-black ${levelConfig.color}`}>
                  {confidence.confidence_score.toFixed(1)}%
                </p>
              </div>
              <div className="text-right">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${levelConfig.bg} ${levelConfig.color} border ${levelConfig.border}`}
                >
                  <span>{levelConfig.icon}</span>
                  {confidence.confidence_level}
                </span>
              </div>
            </div>
          </div>

          {/* Score Breakdown */}
          <div className="grid grid-cols-3 gap-3">
            <ScoreCard
              label="Evidence Quality"
              score={confidence.evidence_quality_score}
            />
            <ScoreCard
              label="Reproduction"
              score={confidence.reproduction_score}
            />
            <ScoreCard
              label="AI Analysis"
              score={confidence.ai_analysis_score}
            />
          </div>

          {/* Verification Status */}
          <div className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <div>
              <p className="text-xs font-semibold uppercase text-zinc-400">
                Verification
              </p>
              <p
                className={`text-sm font-bold ${
                  verificationStatusColors[
                    confidence.verification_status
                  ] || "text-zinc-400"
                }`}
              >
                {confidence.verification_status}
              </p>
            </div>
            <button
              onClick={triggerVerification}
              disabled={loading !== null}
              className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 hover:bg-amber-500/20 transition-colors disabled:opacity-50"
            >
              {loading === "verify" ? "Verifying…" : "Request Verification"}
            </button>
          </div>

          {/* Explanation */}
          <div className="rounded-lg border border-zinc-800/60 bg-zinc-900/30 p-4">
            <p className="text-xs font-semibold uppercase text-zinc-400 mb-1">
              AI Explanation
            </p>
            <p className="text-sm text-zinc-300">{confidence.explanation}</p>
            <p className="mt-2 text-xs text-amber-400/80 italic">
              ⚠ AI generated analysis — Human approval required for all
              remediation actions
            </p>
          </div>

          {/* Verification Probe Result */}
          {verification && (
            <div className="rounded-lg border border-zinc-800/60 bg-zinc-900/30 p-4">
              <p className="text-xs font-semibold uppercase text-zinc-400 mb-1">
                Last Verification Probe
              </p>
              <p className="text-sm text-zinc-300">
                Status:{" "}
                <span
                  className={
                    verificationStatusColors[
                      verification.verification_status
                    ] || "text-zinc-400"
                  }
                >
                  {verification.verification_status}
                </span>{" "}
                | Reproduced:{" "}
                <span
                  className={
                    verification.is_reproduced
                      ? "text-emerald-400"
                      : "text-red-400"
                  }
                >
                  {verification.is_reproduced ? "Yes" : "No"}
                </span>
              </p>
              {verification.probe_output && (
                <pre className="mt-2 rounded bg-zinc-950 p-2 text-xs text-zinc-400 overflow-x-auto">
                  {verification.probe_output}
                </pre>
              )}
            </div>
          )}

          {/* Analyst Review Actions */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <p className="text-xs font-semibold uppercase text-zinc-400 mb-3">
              Analyst Review Actions
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => submitReview("CONFIRM")}
                disabled={loading !== null}
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
              >
                ✓ Confirm Finding
              </button>
              <button
                onClick={() => submitReview("FALSE_POSITIVE")}
                disabled={loading !== null}
                className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-medium text-red-300 hover:bg-red-500/20 transition-colors disabled:opacity-50"
              >
                ✗ Mark False Positive
              </button>
              <button
                onClick={() => submitReview("ACCEPT_RISK")}
                disabled={loading !== null}
                className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs font-medium text-amber-300 hover:bg-amber-500/20 transition-colors disabled:opacity-50"
              >
                ⚡ Accept Risk
              </button>
              <button
                onClick={() => submitReview("REQUEST_MORE_EVIDENCE")}
                disabled={loading !== null}
                className="rounded-lg border border-zinc-600/30 bg-zinc-600/10 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-600/20 transition-colors disabled:opacity-50"
              >
                📋 Request More Evidence
              </button>
            </div>

            {review && (
              <p className="mt-3 text-xs text-emerald-400">
                ✓ Review submitted: {review.decision} at{" "}
                {new Date(review.created_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/* Score breakdown card */
const ScoreCard: React.FC<{ label: string; score: number }> = ({
  label,
  score,
}) => {
  const getColor = () => {
    if (score >= 80) return "text-emerald-400";
    if (score >= 60) return "text-blue-400";
    if (score >= 40) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-center">
      <p className="text-xs font-medium uppercase text-zinc-400">{label}</p>
      <p className={`text-xl font-black ${getColor()}`}>
        {score.toFixed(0)}%
      </p>
    </div>
  );
};
