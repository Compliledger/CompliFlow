"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type SignedReceipt = {
  payload: any;
  signature: string;
};

export default function OrderForm({
  onResult,
}: {
  onResult: (data: {
    intent: any;
    receipt: SignedReceipt;
    decision: { status?: string; reason?: string } | null;
  }) => void;
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
      const res = await api.post<SignedReceipt>("/v1/intent/evaluate", intent);

      // Your backend returns: { payload: { intent, decision }, signature }
      const decision = res.data?.payload?.decision ?? null;

      onResult({
        intent,
        receipt: res.data,
        decision,
      });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 12, maxWidth: 520 }}>
      <h3 style={{ margin: 0 }}>Order Entry</h3>

      <label style={{ display: "grid", gap: 6 }}>
        <span>Session Key</span>
        <input
          value={sessionKey}
          onChange={(e) => setSessionKey(e.target.value)}
          placeholder="session key"
          style={{ padding: 10, borderRadius: 8 }}
        />
      </label>

      <label style={{ display: "grid", gap: 6 }}>
        <span>Wallet Address</span>
        <input
          value={wallet}
          onChange={(e) => setWallet(e.target.value)}
          placeholder="0x..."
          style={{ padding: 10, borderRadius: 8 }}
        />
      </label>

      <div style={{ display: "flex", gap: 10 }}>
        <label style={{ display: "grid", gap: 6, flex: 1 }}>
          <span>Side</span>
          <select
            value={side}
            onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}
            style={{ padding: 10, borderRadius: 8 }}
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </label>

        <label style={{ display: "grid", gap: 6, flex: 2 }}>
          <span>Asset</span>
          <input
            value={asset}
            onChange={(e) => setAsset(e.target.value)}
            placeholder="ytest.usd"
            style={{ padding: 10, borderRadius: 8 }}
          />
        </label>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <label style={{ display: "grid", gap: 6, flex: 1 }}>
          <span>Amount</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            style={{ padding: 10, borderRadius: 8 }}
          />
        </label>

        <label style={{ display: "grid", gap: 6, flex: 1 }}>
          <span>Price</span>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
            style={{ padding: 10, borderRadius: 8 }}
          />
        </label>
      </div>

      <label style={{ display: "grid", gap: 6 }}>
        <span>Jurisdiction</span>
        <select
          value={jurisdiction}
          onChange={(e) => setJurisdiction(e.target.value)}
          style={{ padding: 10, borderRadius: 8 }}
        >
          <option value="US">US</option>
          <option value="EU">EU</option>
          <option value="BLOCKED_REGION">BLOCKED_REGION</option>
        </select>
      </label>

      <button
        onClick={submit}
        disabled={loading}
        style={{
          padding: 12,
          borderRadius: 10,
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Evaluating..." : "Evaluate & Submit"}
      </button>

      {error && (
        <div style={{ color: "#ff6b6b", fontSize: 14 }}>
          Error: {error}
        </div>
      )}
    </div>
  );
}
