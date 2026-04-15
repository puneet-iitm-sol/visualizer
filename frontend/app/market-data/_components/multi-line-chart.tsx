"use client";
import { useMemo } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EChart } from "@/components/charts/echarts-base";
import type { SeriesPayload } from "@/lib/types/market";

const COLORS = ["#22d3ee", "#a78bfa", "#10b981", "#f59e0b", "#ef4444", "#38bdf8", "#facc15"];

interface Props {
  title: string;
  group: string;
  payload: SeriesPayload | undefined;
  height?: number;
  asBar?: boolean;
  totalKey?: string;
}

export function MultiLineChart({ title, group, payload, height = 220, asBar, totalKey }: Props) {
  const option = useMemo(() => {
    if (!payload) {
      return { title: { text: "no data", left: "center", top: "middle", textStyle: { color: "#6b7280" } } };
    }
    const x = (payload.__x__ as number[] | undefined) ?? [];
    const productKeys = Object.keys(payload).filter((k) => k !== "__x__" && k !== "__total__");

    const series: any[] = [];
    productKeys.forEach((p, i) => {
      const ys = payload[p] as number[] | undefined;
      if (!ys) return;
      series.push({
        name: p,
        type: asBar ? "bar" : "line",
        showSymbol: false,
        large: true,
        sampling: asBar ? undefined : "lttb",
        lineStyle: asBar ? undefined : { width: 1.2, color: COLORS[i % COLORS.length] },
        itemStyle: { color: COLORS[i % COLORS.length] },
        data: x.map((t, idx) => [t, ys[idx]]),
      });
    });
    if (totalKey && payload[totalKey]) {
      const ys = payload[totalKey] as number[];
      series.push({
        name: totalKey.replace(/__/g, ""),
        type: "line",
        showSymbol: false,
        lineStyle: { width: 1.6, color: "#ffffff" },
        data: x.map((t, idx) => [t, ys[idx]]),
      });
    }

    return {
      grid: { left: 50, right: 16, top: 22, bottom: 32 },
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { textStyle: { color: "#9ca3af" }, top: 0, type: "scroll" },
      xAxis: { type: "value", scale: true, name: "ts" },
      yAxis: { type: "value", scale: true },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 12, bottom: 6 }],
      series,
    };
  }, [payload, asBar, totalKey]);

  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardBody><EChart option={option} group={group} height={height} /></CardBody>
    </Card>
  );
}
