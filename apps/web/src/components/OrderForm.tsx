"use client";

import { useState } from "react";
import { evaluateIntent } from "@/lib/api";
import { TradeIntent, SignedReceipt } from "@/lib/types";

const DEFAULT_EXPIRES_SECONDS = 60;

export default function OrderForm() {
  const [form, setForm] = useState<Omit<TradeIntent, "expires_at">>({
    session_key: "",
    user_wallet: "",
    side: "BUY",
    amount: 0,
    price: 0,
    asset: "",
  });
  const [result, setResult] = useState<SignedReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === "amount" || name === "price" ? Number(value) : value,
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const intent: TradeIntent = {
        ...form,
        expires_at: Math.floor(Date.now() / 1000) + DEFAULT_EXPIRES_SECONDS,
      };
      const receipt = await evaluateIntent(intent);
      setResult(receipt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="session_key">Session Key</label>
          <input
            id="session_key"
            name="session_key"
            type="text"
            value={form.session_key}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label htmlFor="user_wallet">User Wallet</label>
          <input
            id="user_wallet"
            name="user_wallet"
            type="text"
            value={form.user_wallet}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label htmlFor="side">Side</label>
          <select
            id="side"
            name="side"
            value={form.side}
            onChange={handleChange}
            required
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </div>
        <div>
          <label htmlFor="asset">Asset</label>
          <input
            id="asset"
            name="asset"
            type="text"
            value={form.asset}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label htmlFor="amount">Amount</label>
          <input
            id="amount"
            name="amount"
            type="number"
            min="0"
            step="any"
            value={form.amount}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label htmlFor="price">Price</label>
          <input
            id="price"
            name="price"
            type="number"
            min="0"
            step="any"
            value={form.price}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label htmlFor="jurisdiction">Jurisdiction</label>
          <input
            id="jurisdiction"
            name="jurisdiction"
            type="text"
            value={form.jurisdiction ?? ""}
            onChange={handleChange}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? "Evaluating…" : "Submit Order"}
        </button>
      </form>

      {error && (
        <div role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div>
          <h2>Receipt</h2>
          <p>
            <strong>Decision:</strong> {result.payload.decision}
          </p>
          <details>
            <summary>Raw receipt</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
