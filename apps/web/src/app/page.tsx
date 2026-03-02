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
