"use client";
import { useMemo } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EChart } from "@/components/charts/echarts-base";
import { useLogStore } from "@/lib/store/log-store";

const COLORS = ["#22d3ee", "#a78bfa", "#10b981", "#f59e0b", "#ef4444"];

export function PositionTracker({ group }: { group: string }) {
  const { dashboard } = useLogStore();
  const option = useMemo(() => {
    const pos = dashboard?.position ?? {};
    const products = Object.keys(pos);
    const series = products.map((p, i) => ({
      name: p,
      type: "line",
      step: "end" as const,
      showSymbol: false,
      lineStyle: { color: COLORS[i % COLORS.length], width: 1.2 },
      data: pos[p].x.map((t: number, idx: number) => [t, pos[p].y[idx]]),
    }));
    return {
      grid: { left: 50, right: 16, top: 22, bottom: 36 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "#9ca3af" }, top: 0 },
      xAxis: { type: "value", scale: true, name: "ts" },
      yAxis: { type: "value", scale: true, name: "position" },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 14, bottom: 8 }],
      series,
    };
  }, [dashboard]);

  return (
    <Card>
      <CardHeader><CardTitle>Position over time</CardTitle></CardHeader>
      <CardBody><EChart option={option} group={group} height={220} /></CardBody>
    </Card>
  );
}
