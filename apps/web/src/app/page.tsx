import Link from "next/link";
import ColorBends from "@/components/ColorBends";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 relative">
      <div className="fixed inset-0 -z-10">
        <ColorBends
          colors={["#000000", "#FFD700", "#F5C842", "#FFA500", "#1a1a1a"]}
          rotation={0}
          speed={0.15}
          scale={1.2}
          frequency={0.8}
          warpStrength={1.2}
          mouseInfluence={0.8}
          parallax={0.3}
          noise={0.05}
          transparent
          autoRotate={5}
        />
      </div>
      <div className="max-w-5xl mx-auto text-center space-y-8 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass border border-accent-purple/30 mb-6 animate-slide-down">
          <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          <span className="text-sm font-medium text-white/80">Built on Yellow Network</span>
        </div>
        
        <h1 className="text-6xl md:text-7xl font-display font-bold tracking-tight">
          <span className="text-gradient">CompliFlow</span>
        </h1>
        
        <p className="text-xl md:text-2xl text-white/70 max-w-2xl mx-auto leading-relaxed">
          Programmable execution control layer with{" "}
          <span className="text-white font-semibold">deterministic compliance</span>{" "}
          enforcement and{" "}
          <span className="text-white font-semibold">session-key governance</span>
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-6">
          <Link href="/app">
            <button className="group relative px-8 py-4 bg-gradient-to-r from-accent-yellow to-accent-gold rounded-xl font-semibold text-lg text-black transition-all duration-300 hover:scale-105 hover:shadow-[0_0_40px_rgba(255,215,0,0.8)] overflow-hidden">
              <span className="relative z-10">Launch Dashboard</span>
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            </button>
          </Link>
          
          <button className="px-8 py-4 glass-gold rounded-xl font-semibold text-lg border border-accent-gold/30 hover:border-accent-gold/60 transition-all duration-300 hover:scale-105">
            View Docs
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-12 max-w-4xl mx-auto">
          <div className="glass p-6 rounded-2xl border border-white/10 hover:border-accent-purple/40 transition-all duration-300 hover:scale-105 group">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-yellow to-accent-gold flex items-center justify-center mb-4 group-hover:animate-glow">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Deterministic Compliance</h3>
            <p className="text-white/60 text-sm">Real-time policy evaluation before execution</p>
          </div>
          
          <div className="glass p-6 rounded-2xl border border-white/10 hover:border-accent-gold/40 transition-all duration-300 hover:scale-105 group">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-gold to-accent-amber flex items-center justify-center mb-4 group-hover:animate-glow">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Session Key Security</h3>
            <p className="text-white/60 text-sm">Delegated authority with cryptographic validation</p>
          </div>
          
          <div className="glass p-6 rounded-2xl border border-white/10 hover:border-accent-yellow/40 transition-all duration-300 hover:scale-105 group">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-amber to-accent-yellow flex items-center justify-center mb-4 group-hover:animate-glow">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Signed Receipts</h3>
            <p className="text-white/60 text-sm">Cryptographically verified execution proofs</p>
          </div>
        </div>
      </div>
    </div>
  );
}
