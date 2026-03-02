"use client";

import { useState } from "react";
import OrderForm from "@/components/OrderForm";

type FlowStep =
  | "INTENT_SUBMITTED"
  | "INTENT_EVALUATED"
  | "RECEIPT_SIGNED"
  | "ORDER_SUBMITTED"
  | "MATCHED_OFFCHAIN"
  | "ESCROW_LOCKED"
  | "SETTLED_ONCHAIN";

const STEPS: { key: FlowStep; label: string }[] = [
  { key: "INTENT_SUBMITTED", label: "Intent Submitted" },
  { key: "INTENT_EVALUATED", label: "Policy Evaluated" },
  { key: "RECEIPT_SIGNED", label: "Receipt Signed" },
  { key: "ORDER_SUBMITTED", label: "Order Submitted (Yellow)" },
  { key: "MATCHED_OFFCHAIN", label: "Matched Off-chain" },
  { key: "ESCROW_LOCKED", label: "Escrow Locked" },
  { key: "SETTLED_ONCHAIN", label: "Settled On-chain" },
];

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [step, setStep] = useState<FlowStep>("INTENT_SUBMITTED");

  function stepIndex(s: FlowStep) {
    return STEPS.findIndex((x) => x.key === s);
  }

  return (
    <div style={{ padding: 40, display: "grid", gap: 18 }}>
      <div>
        <h2 style={{ marginBottom: 6 }}>CompliFlow Dashboard</h2>
        <div style={{ opacity: 0.8 }}>
          Deterministic compliance gating + signed receipts (Yellow integration
          in progress)
        </div>
      </div>

      {/* Timeline */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {STEPS.map((s) => {
          const active = stepIndex(step) >= stepIndex(s.key);
          return (
            <div
              key={s.key}
              style={{
                padding: "8px 10px",
                borderRadius: 999,
                border: "1px solid #334155",
                background: active ? "#16a34a" : "transparent",
                color: active ? "white" : "#cbd5e1",
                fontSize: 12,
              }}
            >
              {s.label}
            </div>
          );
        })}
      </div>

      {/* Quick demo controls (manual steps for now) */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {STEPS.map((s) => (
          <button
            key={s.key}
            onClick={() => setStep(s.key)}
            style={{ padding: "8px 10px", borderRadius: 10 }}
          >
            Set: {s.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gap: 18 }}>
        <OrderForm
          onResult={(payload: any) => {
            setData(payload);
            // We can auto-advance basic steps when we get a receipt back
            setStep("RECEIPT_SIGNED");
          }}
        />

        {/* Decision Card */}
        {data?.decision && (
          <div
            style={{
              border: "1px solid #334155",
              borderRadius: 14,
              padding: 16,
              maxWidth: 720,
              background:
                data.decision.status === "PASS" ? "#052e16" : "#3b0a0a",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 6 }}>
              Decision: {data.decision.status ?? "UNKNOWN"}
            </div>
            {data.decision.reason && (
              <div style={{ opacity: 0.9 }}>Reason: {data.decision.reason}</div>
            )}
          </div>
        )}

        {/* Receipt */}
        {data?.receipt && (
          <div style={{ maxWidth: 900 }}>
            <h3 style={{ marginBottom: 8 }}>Signed Receipt</h3>
            <pre
              style={{
                background: "#111",
                padding: 16,
                borderRadius: 12,
                overflow: "auto",
              }}
            >
              {JSON.stringify(data.receipt, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
