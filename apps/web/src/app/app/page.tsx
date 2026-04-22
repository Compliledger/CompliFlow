"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import OrderForm, { type OrderFormResult } from "@/components/OrderForm";
import Link from "next/link";
import ColorBends from "@/components/ColorBends";
import YellowConnect from "@/components/YellowConnect";
import {
  getYellowOrderStatus,
  validateSettlement,
  type SettlementDecision,
} from "@/lib/api";

type FlowStep =
  | "INTENT_SUBMITTED"
  | "DECISION_EVALUATED"
  | "PROOF_GENERATED"
  | "SUBMITTED_TO_YELLOW"
  | "COLLATERAL_VERIFIED"
  | "ESCROW_LOCKED"
  | "MATCHED"
  | "SETTLEMENT_PENDING"
  | "SETTLED";

const STEPS: { key: FlowStep; label: string; icon: string }[] = [
  { key: "INTENT_SUBMITTED", label: "Intent Submitted", icon: "📝" },
  { key: "DECISION_EVALUATED", label: "Decision Evaluated", icon: "🔍" },
  { key: "PROOF_GENERATED", label: "Proof Generated", icon: "🧾" },
  { key: "SUBMITTED_TO_YELLOW", label: "Submitted to Yellow", icon: "🚀" },
  { key: "COLLATERAL_VERIFIED", label: "Collateral Verified", icon: "🛡️" },
  { key: "ESCROW_LOCKED", label: "Escrow Locked", icon: "🔒" },
  { key: "MATCHED", label: "Matched", icon: "🔄" },
  { key: "SETTLEMENT_PENDING", label: "Settlement Pending", icon: "⏳" },
  { key: "SETTLED", label: "Settled", icon: "✅" },
];

// Map a backend Yellow order status (and optional settlement status) to our
// timeline step. Kept defensive: unknown values fall back to the current step
// the caller already reached so progress never visually regresses.
function mapBackendStatusToStep(
  backendStatus: string | undefined,
  details: Record<string, any> | undefined
): FlowStep | null {
  if (!backendStatus) return null;
  const s = backendStatus.toUpperCase();

  const settlementStatus =
    (details?.settlement_status as string | undefined)?.toUpperCase() ?? null;
  const collateralVerified =
    details?.collateral_verified === true ||
    details?.details?.collateral_verified === true;

  if (s === "SETTLED" || s === "SETTLED_ONCHAIN") return "SETTLED";
  if (
    settlementStatus === "PENDING" ||
    settlementStatus === "SETTLEMENT_PENDING" ||
    s === "SETTLEMENT_PENDING"
  )
    return "SETTLEMENT_PENDING";
  if (s === "MATCHED" || s === "MATCHED_OFFCHAIN") return "MATCHED";
  if (s === "ESCROW_LOCKED") return "ESCROW_LOCKED";
  if (collateralVerified) return "COLLATERAL_VERIFIED";
  if (s === "SUBMITTED" || s === "ORDER_SUBMITTED" || s === "PENDING")
    return "SUBMITTED_TO_YELLOW";
  return null;
}

function shortHash(value: string | undefined | null, head = 10, tail = 6) {
  if (!value) return "—";
  if (value.length <= head + tail + 3) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

function formatExpiresAt(unixSeconds: number | undefined | null) {
  if (!unixSeconds) return "—";
  try {
    return new Date(unixSeconds * 1000).toLocaleString();
  } catch {
    return String(unixSeconds);
  }
}

export default function Dashboard() {
  const [data, setData] = useState<OrderFormResult | null>(null);
  const [step, setStep] = useState<FlowStep>("INTENT_SUBMITTED");
  const [backendStatus, setBackendStatus] = useState<{
    status: string;
    details?: Record<string, any>;
    error?: string;
  } | null>(null);
  const [settlement, setSettlement] = useState<SettlementDecision | null>(null);
  const [settlementError, setSettlementError] = useState<string | null>(null);
  const lastSettlementStatusRef = useRef<string | null>(null);

  function stepIndex(s: FlowStep) {
    return STEPS.findIndex((x) => x.key === s);
  }

  // Advance the timeline only forward — never let a transient backend response
  // pull the UI back to an earlier step.
  function advanceStep(target: FlowStep) {
    setStep((current) =>
      stepIndex(target) > stepIndex(current) ? target : current
    );
  }

  // Poll GET /v1/yellow/order/{order_id}/status while we have an order_id and
  // settlement is not yet final.
  useEffect(() => {
    const orderId = data?.orderId;
    if (!orderId) return;

    let cancelled = false;

    async function tick(id: string) {
      try {
        const res = await getYellowOrderStatus(id);
        if (cancelled) return;
        setBackendStatus({
          status: res.status,
          details: res.details,
          error: res.error,
        });
        const mapped = mapBackendStatusToStep(res.status, res.details);
        if (mapped) advanceStep(mapped);
      } catch (err: any) {
        if (cancelled) return;
        setBackendStatus({
          status: "UNKNOWN",
          error: err?.message ?? "Failed to fetch order status",
        });
      }
    }

    // Fire immediately, then poll on an interval until the order is settled.
    tick(orderId);
    const interval = setInterval(() => {
      if (step === "SETTLED") return;
      tick(orderId);
    }, 4000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // We intentionally re-run when the orderId changes; `step` is read inside
    // the interval callback via closure of setStep updater.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.orderId]);

  // Trigger settlement validation as soon as the backend reports an
  // execution status the settlement engine can act on.
  useEffect(() => {
    const orderId = data?.orderId;
    if (!data || !orderId || !backendStatus?.status) return;
    const execStatus = backendStatus.status.toUpperCase();
    const eligible = new Set([
      "MATCHED",
      "MATCHED_OFFCHAIN",
      "ESCROW_LOCKED",
      "SETTLED",
      "SETTLED_ONCHAIN",
    ]);
    if (!eligible.has(execStatus)) return;
    if (lastSettlementStatusRef.current === execStatus) return;
    lastSettlementStatusRef.current = execStatus;

    const normalised =
      execStatus === "MATCHED_OFFCHAIN"
        ? "MATCHED"
        : execStatus === "SETTLED_ONCHAIN"
        ? "SETTLED"
        : execStatus;

    (async () => {
      try {
        const decision = await validateSettlement({
          order_id: orderId,
          intent: data.intent,
          receipt: data.receipt,
          execution_status: normalised,
        });
        setSettlement(decision);
        setSettlementError(null);
      } catch (err: any) {
        setSettlementError(
          err?.response?.data?.detail ??
            err?.message ??
            "Settlement validation failed"
        );
      }
    })();
  }, [data, backendStatus?.status]);

  // Decision-card derivations (kept null-safe so legacy PASS/FAIL still works).
  const decisionInfo = useMemo(() => {
    if (!data?.decision) return null;
    const value =
      data.decision.decision ?? data.decision.status ?? "UNKNOWN";
    const isAllowed =
      value === "ALLOW" || value === "ALLOW_WITH_CONDITIONS" || value === "PASS";
    const reasonText =
      data.decision.human_reason ??
      (Array.isArray(data.decision.reason_codes) &&
      data.decision.reason_codes.length
        ? data.decision.reason_codes.join(", ")
        : data.decision.reason);
    return {
      value,
      isAllowed,
      reasonText,
      policyVersion: data.decision.policy_version,
      conditions: data.decision.conditions,
    };
  }, [data]);

  // Drive the early stages of the timeline directly from the form result so
  // the UI feels responsive even before the first status poll lands.
  useEffect(() => {
    if (!data) return;
    advanceStep("INTENT_SUBMITTED");
    if (data.decision) advanceStep("DECISION_EVALUATED");
    if (data.proofBundle) advanceStep("PROOF_GENERATED");
    if (data.submission?.status) advanceStep("SUBMITTED_TO_YELLOW");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  return (
    <div className="min-h-screen p-6 md:p-10 relative">
      <div className="fixed inset-0 -z-10">
        <ColorBends
          colors={["#000000", "#FFD700", "#F5C842", "#FFA500"]}
          rotation={45}
          speed={0.1}
          scale={1.5}
          frequency={0.6}
          warpStrength={0.8}
          mouseInfluence={0.5}
          parallax={0.2}
          noise={0.03}
          transparent
          autoRotate={3}
        />
      </div>
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between animate-slide-down">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/" className="text-white/60 hover:text-white transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <h1 className="text-4xl font-display font-bold text-gradient">CompliFlow Dashboard</h1>
            </div>
            <p className="text-white/60 text-lg">
              Deterministic compliance gating + signed receipts
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 px-4 py-2 glass-gold rounded-full border border-accent-gold/30">
            <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
            <span className="text-sm font-medium">Yellow Integration Active</span>
          </div>
        </div>

        <div className="glass p-6 rounded-2xl border border-white/10 animate-scale-in">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span className="text-2xl">⚡</span>
              Execution Timeline
            </h2>
            {data?.orderId && (
              <div className="text-xs text-white/60 font-mono">
                order_id:{" "}
                <span className="text-accent-gold">{shortHash(data.orderId)}</span>
                {backendStatus?.status && (
                  <span className="ml-3">
                    backend:{" "}
                    <span className="text-white">{backendStatus.status}</span>
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {STEPS.map((s, idx) => {
              const active = stepIndex(step) >= stepIndex(s.key);
              const isCurrent = stepIndex(step) === stepIndex(s.key);
              return (
                <div key={s.key} className="flex items-center gap-2">
                  <div
                    className={`
                      relative flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all duration-300 whitespace-nowrap
                      ${active ? 'glass-gold border-accent-gold/50 shadow-[0_0_20px_rgba(255,215,0,0.3)]' : 'border border-white/10'}
                      ${isCurrent ? 'animate-glow' : ''}
                    `}
                  >
                    <span className="text-xl">{s.icon}</span>
                    <span className={`text-sm font-medium ${active ? 'text-white' : 'text-white/40'}`}>
                      {s.label}
                    </span>
                    {active && (
                      <div className="absolute inset-0 bg-gradient-to-r from-accent-yellow/20 to-accent-gold/20 rounded-xl -z-10" />
                    )}
                  </div>
                  {idx < STEPS.length - 1 && (
                    <div className={`w-8 h-0.5 ${active ? 'bg-accent-gold/50' : 'bg-white/10'}`} />
                  )}
                </div>
              );
            })}
          </div>
          {backendStatus?.error && (
            <div className="mt-3 text-xs text-red-300/80">
              ⚠️ Status poll error: {backendStatus.error}
            </div>
          )}
        </div>

        <details className="glass p-4 rounded-xl border border-white/10 cursor-pointer group">
          <summary className="text-sm font-medium text-white/60 group-hover:text-white transition-colors">
            🎮 Demo Controls (Testing)
          </summary>
          <div className="flex gap-2 flex-wrap mt-3 pt-3 border-t border-white/10">
            {STEPS.map((s) => (
              <button
                key={s.key}
                onClick={() => setStep(s.key)}
                className="px-3 py-1.5 text-xs rounded-lg glass border border-white/10 hover:border-accent-gold/50 transition-all hover:scale-105"
              >
                {s.icon} {s.label}
              </button>
            ))}
          </div>
        </details>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="animate-slide-up">
            <OrderForm
              onResult={(payload) => {
                setData(payload);
                setBackendStatus(null);
                setSettlement(null);
                setSettlementError(null);
                lastSettlementStatusRef.current = null;
              }}
            />
          </div>

          <div className="space-y-6">
            {decisionInfo && (
              <div
                className={`
                  p-6 rounded-2xl border animate-scale-in
                  ${decisionInfo.isAllowed
                    ? 'bg-gradient-to-br from-accent-yellow/20 to-accent-gold/10 border-accent-yellow/50 shadow-[0_0_30px_rgba(255,215,0,0.3)]'
                    : 'bg-gradient-to-br from-red-500/20 to-pink-500/10 border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.3)]'
                  }
                `}
              >
                <div className="flex items-start gap-3">
                  <span className="text-3xl">
                    {decisionInfo.isAllowed ? "✅" : "❌"}
                  </span>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold mb-2">
                      Decision: {decisionInfo.value}
                    </h3>
                    {decisionInfo.reasonText && (
                      <p className="text-white/80">
                        <span className="font-semibold">Reason:</span>{" "}
                        {decisionInfo.reasonText}
                      </p>
                    )}
                    {decisionInfo.policyVersion && (
                      <p className="text-white/60 text-sm mt-2">
                        <span className="font-semibold">Policy version:</span>{" "}
                        <span className="font-mono">
                          {decisionInfo.policyVersion}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {data?.proofBundle && (
              <div className="glass p-6 rounded-2xl border border-white/10 animate-slide-up">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">🧾</span>
                  <h3 className="text-lg font-semibold">Proof Bundle</h3>
                  {data.proofBundle.proof_version && (
                    <span className="ml-auto text-xs text-white/50 font-mono">
                      v{data.proofBundle.proof_version}
                    </span>
                  )}
                </div>
                <dl className="grid grid-cols-1 gap-3 text-sm">
                  <div className="flex items-start justify-between gap-4">
                    <dt className="text-white/60">proof_hash</dt>
                    <dd
                      className="font-mono text-accent-gold truncate max-w-[60%]"
                      title={data.proofBundle.proof_hash}
                    >
                      {shortHash(data.proofBundle.proof_hash, 12, 8)}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <dt className="text-white/60">policy_version</dt>
                    <dd className="font-mono text-white">
                      {data.proofBundle.decision?.policy_version ??
                        decisionInfo?.policyVersion ??
                        "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <dt className="text-white/60">expires_at</dt>
                    <dd className="font-mono text-white">
                      {formatExpiresAt(data.proofBundle.expires_at)}
                    </dd>
                  </div>
                </dl>
              </div>
            )}

            {(settlement || settlementError) && (
              <div className="glass p-6 rounded-2xl border border-white/10 animate-slide-up">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">🛡️</span>
                  <h3 className="text-lg font-semibold">Settlement Validation</h3>
                </div>
                {settlement && (
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        className={`
                          px-2 py-1 rounded-md text-xs font-semibold
                          ${settlement.decision === "ALLOW"
                            ? "bg-accent-yellow/20 text-accent-yellow border border-accent-yellow/40"
                            : settlement.decision === "ALLOW_WITH_CONDITIONS"
                            ? "bg-accent-gold/20 text-accent-gold border border-accent-gold/40"
                            : "bg-red-500/20 text-red-300 border border-red-500/40"}
                        `}
                      >
                        {settlement.decision}
                      </span>
                      {settlement.policy_version && (
                        <span className="text-xs text-white/50 font-mono">
                          policy {settlement.policy_version}
                        </span>
                      )}
                    </div>
                    {settlement.human_reason && (
                      <p className="text-white/80">{settlement.human_reason}</p>
                    )}
                    {Array.isArray(settlement.reason_codes) &&
                      settlement.reason_codes.length > 0 && (
                        <p className="text-xs text-white/60 font-mono">
                          {settlement.reason_codes.join(", ")}
                        </p>
                      )}
                  </div>
                )}
                {settlementError && (
                  <p className="text-sm text-red-300/80">⚠️ {settlementError}</p>
                )}
              </div>
            )}

            {data?.receipt && (
              <div className="glass p-6 rounded-2xl border border-white/10 animate-slide-up">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">🔐</span>
                  <h3 className="text-lg font-semibold">Signed Receipt</h3>
                </div>
                <div className="relative">
                  <pre className="bg-black/40 p-4 rounded-xl overflow-auto text-xs border border-white/5 max-h-96 font-mono">
                    {JSON.stringify(data.receipt, null, 2)}
                  </pre>
                  <div className="absolute top-2 right-2">
                    <button
                      onClick={() => navigator.clipboard.writeText(JSON.stringify(data.receipt, null, 2))}
                      className="px-3 py-1.5 text-xs glass rounded-lg border border-white/10 hover:border-accent-gold/50 transition-all"
                    >
                      📋 Copy
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <YellowConnect />
    </div>
  );
}
