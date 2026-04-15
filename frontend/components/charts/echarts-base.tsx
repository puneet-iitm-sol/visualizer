"use client";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  LineChart, BarChart, ScatterChart, HeatmapChart, CustomChart,
} from "echarts/charts";
import {
  GridComponent, TooltipComponent, LegendComponent, DataZoomComponent,
  MarkLineComponent, MarkPointComponent, AxisPointerComponent,
  TitleComponent, VisualMapComponent,
} from "echarts/components";
import { useEffect, useRef } from "react";

echarts.use([
  CanvasRenderer,
  LineChart, BarChart, ScatterChart, HeatmapChart, CustomChart,
  GridComponent, TooltipComponent, LegendComponent, DataZoomComponent,
  MarkLineComponent, MarkPointComponent, AxisPointerComponent,
  TitleComponent, VisualMapComponent,
]);

type ECInstance = echarts.ECharts;

interface Props {
  option: echarts.EChartsCoreOption;
  className?: string;
  height?: number | string;
  group?: string;       // chart-sync group
  onInit?: (chart: ECInstance) => void;
  onClickPoint?: (params: { seriesName?: string; dataIndex: number; data: unknown }) => void;
}

export function EChart({ option, className, height = 280, group, onInit, onClickPoint }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECInstance | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current, "dark", {
      renderer: "canvas",
    });
    chartRef.current = chart;
    if (group) chart.group = group;
    echarts.connect(group ?? "default");
    onInit?.(chart);

    if (onClickPoint) {
      chart.on("click", (p: any) => {
        if (p && typeof p.dataIndex === "number") onClickPoint(p);
      });
    }

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [group]);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true, lazyUpdate: true });
  }, [option]);

  return <div ref={containerRef} className={className} style={{ width: "100%", height }} />;
}
