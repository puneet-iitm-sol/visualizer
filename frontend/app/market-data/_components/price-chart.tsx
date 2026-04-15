"use client";
import { useMemo } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EChart } from "@/components/charts/echarts-base";
import { useMarketStore } from "@/lib/store/market-store";

const COLORS = ["#22d3ee", "#a78bfa", "#10b981", "#f59e0b", "#ef4444", "#38bdf8", "#facc15"];

export function PriceChart({ group }: { group: string }) {
  const { query, set, filterProducts } = useMarketStore();

  const option = useMemo(() => {
    const mid = query?.series.mid ?? {};
    const trades = query?.series.trades ?? {};
    const products = Object.keys(mid).filter((k) => k !== "__x__");
    const x = (mid.__x__ as number[] | undefined) ?? [];

    const series: any[] = [];
    products.forEach((p, i) => {
      const ys = mid[p] as number[] | undefined;
      if (!ys) return;
      series.push({
        name: `${p} mid`,
        type: "line",
        showSymbol: false,
        sampling: "lttb",
        large: true,
        lineStyle: { width: 1.2, color: COLORS[i % COLORS.length] },
        data: x.map((t, idx) => [t, ys[idx]]),
      });
      const tr = trades[p] ?? [];
      if (tr.length) {
        series.push({
          name: `${p} fills`,
          type: "scatter",
          symbolSize: 6,
          itemStyle: { color: COLORS[i % COLORS.length], opacity: 0.7 },
          data: tr.map((t) => [t.ts, t.px, t.qty]),
          tooltip: {
            formatter: (p: any) => `ts ${p.value[0]}<br/>px ${p.value[1]}<br/>qty ${p.value[2]}`,
          },
        });
      }
    });

    return {
      grid: { left: 50, right: 16, top: 20, bottom: 36 },
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      xAxis: { type: "value", name: "ts", scale: true },
      yAxis: { type: "value", scale: true },
      dataZoom: [
        { type: "inside", throttle: 50 },
        { type: "slider", height: 14, bottom: 8 },
      ],
      legend: { textStyle: { color: "#9ca3af" }, top: 0, type: "scroll" },
      series,
    };
  }, [query, filterProducts]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price · Bid/Ask/Mid + executions</CardTitle>
      </CardHeader>
      <CardBody>
        <EChart
          option={option}
          group={group}
          height={320}
          onClickPoint={(p) => {
            const v = (p.data as [number, number]) ?? null;
            if (!v) return;
            const product = (p.seriesName ?? "").split(" ")[0];
            set({ selected: { ts: v[0], product } });
          }}
        />
      </CardBody>
    </Card>
  );
}
