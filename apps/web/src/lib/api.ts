import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 20000
});

// ----- Typed helpers for the expanded backend surface -----

export type YellowOrderStatusResponse = {
  status: string;
  error?: string;
  message?: string;
  details?: Record<string, any>;
};

export async function getYellowOrderStatus(
  orderId: string
): Promise<YellowOrderStatusResponse> {
  const res = await api.get<YellowOrderStatusResponse>(
    `/v1/yellow/order/${encodeURIComponent(orderId)}/status`
  );
  return res.data;
}

export type SettlementDecision = {
  decision: "ALLOW" | "DENY" | "ALLOW_WITH_CONDITIONS" | string;
  reason_codes?: string[];
  human_reason?: string;
  conditions?: Record<string, any>;
  policy_version?: string;
  settlement_context?: Record<string, any>;
};

export async function validateSettlement(input: {
  order_id: string;
  intent: any;
  receipt: any;
  execution_status: string;
  proofs?: Record<string, any>;
}): Promise<SettlementDecision> {
  const res = await api.post<SettlementDecision>(
    "/v1/settlement/validate",
    input
  );
  return res.data;
}
