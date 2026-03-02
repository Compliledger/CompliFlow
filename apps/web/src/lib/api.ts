import { TradeIntent, SignedReceipt } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function evaluateIntent(
  intent: TradeIntent
): Promise<SignedReceipt> {
  const res = await fetch(`${API_URL}/v1/intent/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(intent),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<SignedReceipt>;
}
