"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type SignedReceipt = {
  payload: any;
  signature: string;
  receipt_hash?: string;
  order_id?: string;
  proof_bundle?: any;
};

export type DecisionPayload = {
  // Legacy PASS/FAIL shape (still supported by older flows)
  status?: string;
  reason?: string;
  // New v1 policy-engine shape
  decision?: "ALLOW" | "DENY" | "ALLOW_WITH_CONDITIONS" | string;
  reason_codes?: string[];
  human_reason?: string;
  conditions?: Record<string, any>;
  policy_version?: string;
};

export type OrderFormResult = {
  intent: any;
  receipt: SignedReceipt;
  decision: DecisionPayload | null;
  proofBundle: any | null;
  orderId: string | null;
  submission: { status?: string; details?: any } | null;
};

export default function OrderForm({
  onResult,
}: {
  onResult: (data: OrderFormResult) => void;
}) {
  const [sessionKey, setSessionKey] = useState("demo-session");
  const [wallet, setWallet] = useState("0x123");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [asset, setAsset] = useState("ytest.usd");
  const [amount, setAmount] = useState<number>(10);
  const [price, setPrice] = useState<number>(1);
  const [jurisdiction, setJurisdiction] = useState("US");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    setError(null);

    const intent = {
      session_key: sessionKey,
      user_wallet: wallet,
      side,
      asset,
      amount: Number(amount),
      price: Number(price),
      jurisdiction,
      expires_at: Math.floor(Date.now() / 1000) + 60 * 30,
    };

    try {
      // Step 1: Evaluate intent — runs policy engine and returns a signed compliance receipt
      const res = await api.post<SignedReceipt>("/v1/intent/evaluate", intent);
      const receipt = res.data;
      const decision: DecisionPayload | null =
        receipt?.payload?.decision ?? null;
      const proofBundle = receipt?.proof_bundle ?? null;
      const orderId = receipt?.order_id ?? null;

      // Step 2: Forward to Yellow when the policy engine allows the trade.
      // Support both the legacy {status:"PASS"} and the v1 ALLOW/ALLOW_WITH_CONDITIONS shapes.
      const decisionValue =
        decision?.decision ?? decision?.status ?? "UNKNOWN";
      const isAllowed =
        decisionValue === "ALLOW" ||
        decisionValue === "ALLOW_WITH_CONDITIONS" ||
        decisionValue === "PASS";

      let submission: OrderFormResult["submission"] = null;
      if (isAllowed) {
        try {
          const submitRes = await api.post<{ order_id?: string; status?: string }>(
            "/v1/yellow/order/submit",
            { intent, receipt }
          );
          submission = {
            status: submitRes.data?.status,
            details: submitRes.data,
          };
          console.log("✅ Order submitted to Yellow Network via backend.");
        } catch (submitErr: any) {
          console.error(
            "Yellow Network submission failed:",
            submitErr?.response?.data ?? submitErr?.message
          );
          setError(
            submitErr?.response?.data?.detail?.error ??
              submitErr?.message ??
              "Order submission to Yellow Network failed"
          );
        }
      }

      onResult({
        intent,
        receipt,
        decision,
        proofBundle,
        orderId: submission?.details?.order_id ?? orderId,
        submission,
      });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="glass p-6 rounded-2xl border border-white/10 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-2xl">📊</span>
        <h3 className="text-2xl font-display font-bold text-gradient">Order Entry</h3>
      </div>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-white/80 flex items-center gap-2">
          <span>🔑</span> Session Key
        </span>
        <input
          value={sessionKey}
          onChange={(e) => setSessionKey(e.target.value)}
          placeholder="demo-session"
          className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white placeholder:text-white/30 focus:border-accent-gold/50 focus:ring-2 focus:ring-accent-gold/20 transition-all outline-none"
        />
      </label>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-white/80 flex items-center gap-2">
          <span>👛</span> Wallet Address
        </span>
        <input
          value={wallet}
          onChange={(e) => setWallet(e.target.value)}
          placeholder="0x..."
          className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white placeholder:text-white/30 focus:border-accent-purple/50 focus:ring-2 focus:ring-accent-purple/20 transition-all outline-none font-mono"
        />
      </label>

      <div className="grid grid-cols-3 gap-3">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-white/80 flex items-center gap-2">
            <span>📈</span> Side
          </span>
          <select
            value={side}
            onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}
            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white focus:border-accent-purple/50 focus:ring-2 focus:ring-accent-purple/20 transition-all outline-none cursor-pointer"
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </label>

        <label className="block space-y-2 col-span-2">
          <span className="text-sm font-medium text-white/80 flex items-center gap-2">
            <span>💎</span> Asset
          </span>
          <input
            value={asset}
            onChange={(e) => setAsset(e.target.value)}
            placeholder="ytest.usd"
            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white placeholder:text-white/30 focus:border-accent-gold/50 focus:ring-2 focus:ring-accent-gold/20 transition-all outline-none"
          />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-white/80 flex items-center gap-2">
            <span>💰</span> Amount
          </span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white placeholder:text-white/30 focus:border-accent-gold/50 focus:ring-2 focus:ring-accent-gold/20 transition-all outline-none"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-white/80 flex items-center gap-2">
            <span>💵</span> Price
          </span>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white placeholder:text-white/30 focus:border-accent-gold/50 focus:ring-2 focus:ring-accent-gold/20 transition-all outline-none"
          />
        </label>
      </div>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-white/80 flex items-center gap-2">
          <span>🌍</span> Jurisdiction
        </span>
        <select
          value={jurisdiction}
          onChange={(e) => setJurisdiction(e.target.value)}
          className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white focus:border-accent-purple/50 focus:ring-2 focus:ring-accent-purple/20 transition-all outline-none cursor-pointer"
        >
          <option value="US">🇺🇸 United States</option>
          <option value="EU">🇪🇺 European Union</option>
          <option value="BLOCKED_REGION">🚫 Blocked Region</option>
        </select>
      </label>

      <button
        onClick={submit}
        disabled={loading}
        className={`
          w-full px-6 py-4 mt-2 rounded-xl font-semibold text-lg transition-all duration-300
          ${loading 
            ? 'bg-white/10 cursor-not-allowed opacity-50' 
            : 'bg-gradient-to-r from-accent-yellow to-accent-gold text-black hover:scale-[1.02] hover:shadow-[0_0_40px_rgba(255,215,0,0.8)] active:scale-[0.98]'
          }
          relative overflow-hidden group
        `}
      >
        <span className="relative z-10 flex items-center justify-center gap-2">
          {loading ? (
            <>
              <span className="animate-spin">⚙️</span>
              Evaluating...
            </>
          ) : (
            <>
              <span>🚀</span>
              Evaluate & Submit Intent
            </>
          )}
        </span>
        {!loading && (
          <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
        )}
      </button>

      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-xl animate-scale-in">
          <div className="flex items-start gap-2">
            <span className="text-xl">⚠️</span>
            <div>
              <div className="font-semibold text-red-400">Error</div>
              <div className="text-sm text-red-300/80">{error}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
