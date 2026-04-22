"use client";

import { useState } from "react";
import OrderForm from "@/components/OrderForm";
import Link from "next/link";
import ColorBends from "@/components/ColorBends";
import YellowConnect from "@/components/YellowConnect";

type FlowStep =
  | "INTENT_SUBMITTED"
  | "INTENT_EVALUATED"
  | "RECEIPT_SIGNED"
  | "ORDER_SUBMITTED"
  | "MATCHED_OFFCHAIN"
  | "ESCROW_LOCKED"
  | "SETTLED_ONCHAIN";

const STEPS: { key: FlowStep; label: string; icon: string }[] = [
  { key: "INTENT_SUBMITTED", label: "Intent Submitted", icon: "📝" },
  { key: "INTENT_EVALUATED", label: "Policy Evaluated", icon: "🔍" },
  { key: "RECEIPT_SIGNED", label: "Receipt Signed", icon: "✍️" },
  { key: "ORDER_SUBMITTED", label: "Order Submitted", icon: "🚀" },
  { key: "MATCHED_OFFCHAIN", label: "Matched Off-chain", icon: "🔄" },
  { key: "ESCROW_LOCKED", label: "Escrow Locked", icon: "🔒" },
  { key: "SETTLED_ONCHAIN", label: "Settled On-chain", icon: "✅" },
];

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [step, setStep] = useState<FlowStep>("INTENT_SUBMITTED");

  function stepIndex(s: FlowStep) {
    return STEPS.findIndex((x) => x.key === s);
  }

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
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            Execution Timeline
          </h2>
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
              onResult={(payload: any) => {
                setData(payload);
                setStep("RECEIPT_SIGNED");
              }}
            />
          </div>

          <div className="space-y-6">
            {data?.decision && (() => {
              const decisionValue = data.decision.decision ?? data.decision.status ?? "UNKNOWN";
              const isAllowed = decisionValue === "ALLOW" || decisionValue === "ALLOW_WITH_CONDITIONS" || decisionValue === "PASS";
              const reasonText = data.decision.human_reason
                ?? (Array.isArray(data.decision.reason_codes) && data.decision.reason_codes.length
                  ? data.decision.reason_codes.join(", ")
                  : data.decision.reason);
              return (
              <div
                className={`
                  p-6 rounded-2xl border animate-scale-in
                  ${isAllowed
                    ? 'bg-gradient-to-br from-accent-yellow/20 to-accent-gold/10 border-accent-yellow/50 shadow-[0_0_30px_rgba(255,215,0,0.3)]' 
                    : 'bg-gradient-to-br from-red-500/20 to-pink-500/10 border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.3)]'
                  }
                `}
              >
                <div className="flex items-start gap-3">
                  <span className="text-3xl">
                    {isAllowed ? "✅" : "❌"}
                  </span>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold mb-2">
                      Decision: {decisionValue}
                    </h3>
                    {reasonText && (
                      <p className="text-white/80">
                        <span className="font-semibold">Reason:</span> {reasonText}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              );
            })()}

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
