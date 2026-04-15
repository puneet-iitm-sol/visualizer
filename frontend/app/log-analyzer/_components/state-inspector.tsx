"use client";
import { useEffect } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { useLogStore } from "@/lib/store/log-store";
import { logsApi } from "@/lib/api/logs";
import { fmtNum, fmtTs } from "@/lib/utils/format";

export function StateInspector() {
  const { sessionId, replay, state, set } = useLogStore();

  useEffect(() => {
    if (!sessionId || replay.ts == null) return;
    let cancelled = false;
    logsApi
      .state(sessionId, replay.ts)
      .then((s) => !cancelled && set({ state: s }))
      .catch((e) => !cancelled && set({ error: (e as Error).message }));
    return () => {
      cancelled = true;
    };
  }, [sessionId, replay.ts, set]);

  return (
    <Card className="sticky top-16">
      <CardHeader>
        <CardTitle>State @ {replay.ts != null ? fmtTs(replay.ts) : "—"}</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4 max-h-[calc(100vh-9rem)] overflow-auto">
        {!state ? (
          <p className="text-xs text-muted">Click any chart point or press play.</p>
        ) : (
          <>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Positions</h4>
              <table className="w-full text-xs font-mono">
                <tbody>
                  {Object.entries(state.positions).map(([p, v]) => (
                    <tr key={p}>
                      <td className="text-muted">{p}</td>
                      <td className={`text-right ${v > 0 ? "text-bull" : v < 0 ? "text-bear" : ""}`}>{v}</td>
                    </tr>
                  ))}
                  {Object.keys(state.positions).length === 0 && <tr><td className="text-muted">none</td></tr>}
                </tbody>
              </table>
            </section>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Fills at tick</h4>
              {state.fills_at_tick.length === 0 ? (
                <p className="text-xs text-muted">none</p>
              ) : (
                <ul className="text-xs font-mono space-y-1">
                  {state.fills_at_tick.map((f, i) => (
                    <li key={i}>{f.symbol}: {fmtNum(f.price)} × {f.quantity} <span className="text-muted">({f.buyer ?? "?"} ← {f.seller ?? "?"})</span></li>
                  ))}
                </ul>
              )}
            </section>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Quotes / metrics</h4>
              <div className="text-xs font-mono space-y-1">
                {Object.entries(state.metrics).map(([p, m]) => (
                  <div key={p} className="flex justify-between">
                    <span className="text-muted">{p}</span>
                    <span>mid {fmtNum(m.mid_price)} · spr {fmtNum(m.spread)} · pnl {fmtNum(m.pnl)}</span>
                  </div>
                ))}
              </div>
            </section>
            <section>
              <h4 className="text-xs uppercase text-muted mb-2">Sandbox window</h4>
              <ul className="text-xs font-mono space-y-1 max-h-48 overflow-auto">
                {state.sandbox_window.map((r) => (
                  <li
                    key={r.line_no}
                    className={r.timestamp === replay.ts ? "text-accent" : "text-muted"}
                  >
                    {r.timestamp != null ? fmtTs(r.timestamp) : `#${r.line_no}`} · {r.text}
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
