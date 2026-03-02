export type TradeIntent = {
  session_key: string;
  user_wallet: string;
  side: "BUY" | "SELL";
  amount: number;
  price: number;
  asset: string;
  expires_at: number;
  jurisdiction?: string;
};
