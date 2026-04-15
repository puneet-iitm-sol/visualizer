"use client";
import { useMemo } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EChart } from "@/components/charts/echarts-base";
import { useLogStore } from "@/lib/store/log-store";

const COLORS = ["#22d3ee", "#a78bfa", "#10b981", "#f59e0b", "#ef4444"];

export function AlgoPnl({ group }: { group: string }) {
  const { dashboard, setReplay, set } = useLogStore();

  const option = useMemo(() => {
    const pnl = dashboard?.algo_pnl ?? {};
    const x = (pnl.__x__ as number[] | undefined) ?? [];
    const products = Object.keys(pnl).filter((k) => k !== "__x__" && k !== "__total__");
    const series: any[] = [];
    products.forEach((p, i) => {
      const ys = pnl[p] as number[] | undefined;
      if (!ys) return;
      series.push({
        name: p, type: "line", showSymbol: false, sampling: "lttb", large: true,
        lineStyle: { color: COLORS[i % COLORS.length], width: 1.2 },
        data: x.map((t, idx) => [t, ys[idx]]),
      });
    });
    if (pnl.__total__) {
      const ys = pnl.__total__ as number[];
      series.push({
        name: "total", type: "line", showSymbol: false,
        lineStyle: { color: "#ffffff", width: 1.6 },
        data: x.map((t, idx) => [t, ys[idx]]),
      });
    }
    return {
      grid: { left: 50, right: 16, top: 22, bottom: 36 },
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { textStyle: { color: "#9ca3af" }, top: 0, type: "scroll" },
      xAxis: { type: "value", scale: true, name: "ts" },
      yAxis: { type: "value", scale: true },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 14, bottom: 8 }],
      series,
    };
  }, [dashboard]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Algo cumulative PnL</CardTitle>
      </CardHeader>
      <CardBody>
        <EChart
          option={option}
          group={group}
          height={260}
          onClickPoint={(p) => {
            const v = (p.data as [number, number]) ?? null;
            if (v) {
              setReplay({ ts: v[0], playing: false });
              set({ state: null });
            }
          }}
        />
      </CardBody>
    </Card>
  );
}
