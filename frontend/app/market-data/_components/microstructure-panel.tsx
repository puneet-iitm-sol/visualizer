"use client";
import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useMarketStore } from "@/lib/store/market-store";
import { marketApi } from "@/lib/api/market";
import { fmtNum, fmtTs } from "@/lib/utils/format";
import type { SnapshotResponse } from "@/lib/types/market";
import { X } from "lucide-react";

export function MicrostructurePanel() {
  const { sessionId, selected, set } = useMarketStore();
  const [snap, setSnap] = useState<SnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId || !selected) return;
    setLoading(true);
    setErr(null);
    marketApi
      .snapshot(sessionId, { ts: selected.ts, product: selected.product, day: selected.day, context: 5 })
      .then(setSnap)
      .catch((e) => setErr((e as Error).message))
      .finally(() => setLoading(false));
  }, [sessionId, selected]);

  if (!selected) return null;

  return (
    <Card className="sticky top-16 max-h-[calc(100vh-5rem)] overflow-auto">
      <CardHeader>
        <CardTitle>Microstructure · {selected.product} @ {fmtTs(selected.ts)}</CardTitle>
        <Button size="icon" variant="ghost" onClick={() => set({ selected: null })}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardBody className="space-y-4">
        {loading && <p className="text-xs text-muted">Loading…</p>}
        {err && <p className="text-xs text-bear">{err}</p>}
        {snap && snap.book && (
          <>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Order book</h4>
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-muted">
                    <th className="text-right">Bid qty</th>
                    <th className="text-right">Bid px</th>
                    <th className="text-right">Ask px</th>
                    <th className="text-right">Ask qty</th>
                  </tr>
                </thead>
                <tbody>
                  {[0, 1, 2].map((i) => (
                    <tr key={i}>
                      <td className="text-right text-bull">{snap.book!.bids[i][1] ?? "—"}</td>
                      <td className="text-right">{snap.book!.bids[i][0] ?? "—"}</td>
                      <td className="text-right">{snap.book!.asks[i][0] ?? "—"}</td>
                      <td className="text-right text-bear">{snap.book!.asks[i][1] ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Metrics</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs font-mono">
                {Object.entries(snap.metrics).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-muted">{k}</span>
                    <span>{typeof v === "number" ? fmtNum(v, 4) : "—"}</span>
                  </div>
                ))}
              </div>
            </section>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Trades at tick ({snap.trades_at_ts.length})</h4>
              {snap.trades_at_ts.length === 0 ? (
                <p className="text-xs text-muted">none</p>
              ) : (
                <ul className="text-xs font-mono space-y-1 max-h-32 overflow-auto">
                  {snap.trades_at_ts.map((t, i) => (
                    <li key={i}>
                      {fmtNum(t.px, 2)} × {t.qty} <span className="text-muted">({t.buyer ?? "?"} ← {t.seller ?? "?"})</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">±5 context</h4>
              <ul className="text-xs font-mono space-y-1 max-h-40 overflow-auto">
                {snap.context.map((c) => (
                  <li
                    key={c.timestamp}
                    className={c.timestamp === snap.timestamp ? "text-accent" : "text-muted"}
                  >
                    {fmtTs(c.timestamp)} · mid {fmtNum(c.mid_price)} · spr {fmtNum(c.spread)} · vol {c.trade_volume}
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </CardBody>
    </Card>
  );
}
