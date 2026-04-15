"use client";
import { useEffect, useMemo, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EChart } from "@/components/charts/echarts-base";
import { useLogStore } from "@/lib/store/log-store";
import { logsApi } from "@/lib/api/logs";
import type { CompareResponse } from "@/lib/types/log";

const COLORS = ["#22d3ee", "#a78bfa"];

export function ComparePanel({ group }: { group: string }) {
  const { sessionId, compareSessionId } = useLogStore();
  const [data, setData] = useState<CompareResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId || !compareSessionId) {
      setData(null);
      return;
    }
    logsApi.compare([sessionId, compareSessionId]).then(setData).catch((e) => setErr((e as Error).message));
  }, [sessionId, compareSessionId]);

  const option = useMemo(() => {
    if (!data) return { title: { text: "no comparison loaded", left: "center", top: "middle", textStyle: { color: "#6b7280" } } };
    const series = data.sids.map((sid, i) => {
      const p = data.pnl[sid];
      return {
        name: sid.slice(0, 8),
        type: "line",
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { color: COLORS[i % COLORS.length], width: 1.4 },
        data: p.x.map((t, idx) => [t, p.y[idx]]),
      };
    });
    return {
      grid: { left: 50, right: 16, top: 22, bottom: 36 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "#9ca3af" }, top: 0 },
      xAxis: { type: "value", scale: true, name: "ts" },
      yAxis: { type: "value", scale: true },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 14, bottom: 8 }],
      series,
    };
  }, [data]);

  if (!compareSessionId) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comparison · PnL overlay</CardTitle>
        <span className="text-xs text-muted">{data ? `${data.divergences.length} divergences` : ""}</span>
      </CardHeader>
      <CardBody className="space-y-3">
        {err && <p className="text-xs text-bear">{err}</p>}
        <EChart option={option} group={group} height={220} />
        {data && data.divergences.length > 0 && (
          <div className="max-h-32 overflow-auto text-xs font-mono border-t border-border pt-2">
            <p className="text-muted mb-1">First {data.divergences.length} divergences:</p>
            <ul className="space-y-1">
              {data.divergences.slice(0, 50).map((d, i) => (
                <li key={i}>
                  ts {d.ts} · {d.product} · {data.sids.map((sid) => `${sid.slice(0, 6)}=${d[sid] ?? "—"}`).join("  ")}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
