export interface TradeIntent {
  session_key: string;
  user_wallet: string;
  side: "BUY" | "SELL";
  amount: number;
  price: number;
  asset: string;
  expires_at: number;
  jurisdiction?: string;
}

export interface SignedReceipt {
  payload: {
    intent: TradeIntent;
    decision: string;
  };
  signature: string;
}
