import Link from "next/link";

export default function Home() {
  return (
    <div style={{ padding: 40 }}>
      <h1>CompliFlow</h1>
      <p>Programmable execution control layer on Yellow Network.</p>
      <Link href="/app">
        <button style={{ marginTop: 20 }}>Open Dashboard</button>
      </Link>
    </div>
  );
}

"use client";

import { useState } from "react";
import OrderForm from "@/components/OrderForm";

export default function Dashboard() {
  const [result, setResult] = useState<any>(null);

  return (
    <div style={{ padding: 40 }}>
      <h2>CompliFlow Dashboard</h2>

      <OrderForm onResult={(data) => setResult(data)} />

      {result && (
        <pre style={{ marginTop: 20, background: "#111", padding: 20 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
