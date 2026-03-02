"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function OrderForm({ onResult }: any) {
  const [amount, setAmount] = useState(10);
  const [price, setPrice] = useState(1);
  const [jurisdiction, setJurisdiction] = useState("US");

  async function submit() {
    const payload = {
      session_key: "demo-session",
      user_wallet: "0x123",
      side: "BUY",
      asset: "ytest.usd",
      amount,
      price,
      jurisdiction,
      expires_at: Math.floor(Date.now() / 1000) + 1800
    };

    const res = await api.post("/v1/intent/evaluate", payload);
    onResult(res.data);
  }

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <input type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
      <input type="number" value={price} onChange={(e) => setPrice(Number(e.target.value))} />

      <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
        <option value="US">US</option>
        <option value="BLOCKED_REGION">BLOCKED_REGION</option>
      </select>

      <button onClick={submit}>Evaluate</button>
    </div>
  );
}
