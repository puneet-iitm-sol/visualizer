import Link from "next/link";
import { Activity, ScrollText } from "lucide-react";

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl py-16">
      <h1 className="text-3xl font-semibold tracking-tight">IMC Prosperity Suite</h1>
      <p className="mt-2 text-muted">Two independent modules. Pick a workspace.</p>
      <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/market-data"
          className="rounded-lg border border-border bg-panel p-6 hover:border-accent transition-colors"
        >
          <Activity className="h-6 w-6 text-accent" />
          <h2 className="mt-3 text-xl font-medium">Market Data Explorer</h2>
          <p className="mt-2 text-sm text-muted">
            Upload Prosperity prices + trades CSVs. Cross-filtered charts,
            order-book depth, microstructure inspector.
          </p>
        </Link>
        <Link
          href="/log-analyzer"
          className="rounded-lg border border-border bg-panel p-6 hover:border-accent2 transition-colors"
        >
          <ScrollText className="h-6 w-6 text-accent2" />
          <h2 className="mt-3 text-xl font-medium">Submission Log Analyzer</h2>
          <p className="mt-2 text-sm text-muted">
            Parse `.log` files. Algo PnL, position tracker, sandbox debug
            inspector with timestamp replay.
          </p>
        </Link>
      </div>
    </div>
  );
}
