"use client";

import { useState } from "react";
import OrderForm from "@/components/OrderForm";

export default function Dashboard() {
  const [result, setResult] = useState<any>(null);

  return (
    <div style={{ padding: 40 }}>
      <h2>CompliFlow Dashboard</h2>

      <OrderForm onResult={(data: any) => setResult(data)} />

      {result && (
        <pre
          style={{
            marginTop: 20,
            background: "#111",
            padding: 20,
            overflow: "auto"
          }}
        >
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
