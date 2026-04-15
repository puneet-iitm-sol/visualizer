"use client";
import { useMemo, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EChart } from "@/components/charts/echarts-base";
import { useMarketStore } from "@/lib/store/market-store";

export function OrderBookDepth({ group }: { group: string }) {
  const { query } = useMarketStore();
  const products = Object.keys(query?.series.depth ?? {});
  const [active, setActive] = useState<string | null>(null);
  const product = active ?? products[0] ?? null;

  const option = useMemo(() => {
    if (!product || !query?.series.depth?.[product]) {
      return { title: { text: "no depth data", left: "center", top: "middle", textStyle: { color: "#6b7280" } } };
    }
    const d = query.series.depth[product];
    const x = d.__x__;
    const lvl = (side: "bid" | "ask", i: number, sign: 1 | -1) =>
      x.map((t, idx) => [t, sign * (d[side][idx]?.[i] ?? 0)]);

    return {
      grid: { left: 50, right: 16, top: 24, bottom: 36 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "#9ca3af" }, top: 0 },
      xAxis: { type: "value", scale: true, name: "ts" },
      yAxis: { type: "value", name: "± qty" },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 14, bottom: 8 }],
      series: [
        { name: "bid L1", type: "line", stack: "bids", areaStyle: { opacity: 0.4 }, color: "#10b981", showSymbol: false, data: lvl("bid", 0, 1) },
        { name: "bid L2", type: "line", stack: "bids", areaStyle: { opacity: 0.3 }, color: "#34d399", showSymbol: false, data: lvl("bid", 1, 1) },
        { name: "bid L3", type: "line", stack: "bids", areaStyle: { opacity: 0.2 }, color: "#6ee7b7", showSymbol: false, data: lvl("bid", 2, 1) },
        { name: "ask L1", type: "line", stack: "asks", areaStyle: { opacity: 0.4 }, color: "#ef4444", showSymbol: false, data: lvl("ask", 0, -1) },
        { name: "ask L2", type: "line", stack: "asks", areaStyle: { opacity: 0.3 }, color: "#f87171", showSymbol: false, data: lvl("ask", 1, -1) },
        { name: "ask L3", type: "line", stack: "asks", areaStyle: { opacity: 0.2 }, color: "#fca5a5", showSymbol: false, data: lvl("ask", 2, -1) },
      ],
    };
  }, [product, query]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Order book depth (3 levels)</CardTitle>
        <select
          value={product ?? ""}
          onChange={(e) => setActive(e.target.value)}
          className="bg-bg border border-border rounded-md text-xs px-2 h-7 text-text"
        >
          {products.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </CardHeader>
      <CardBody>
        <EChart option={option} group={group} height={260} />
      </CardBody>
    </Card>
  );
}
