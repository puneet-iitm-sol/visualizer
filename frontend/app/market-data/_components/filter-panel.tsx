"use client";
import { useEffect } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { MultiSelect } from "@/components/ui/multi-select";
import { Input } from "@/components/ui/input";
import { useMarketStore } from "@/lib/store/market-store";
import { marketApi } from "@/lib/api/market";

const SERIES = ["mid", "bid_1", "ask_1", "spread", "volume", "pnl", "trades", "microprice", "wobi"] as const;

export function FilterPanel() {
  const s = useMarketStore();

  // Auto-fetch series whenever filters or session change.
  useEffect(() => {
    if (!s.sessionId || !s.meta) return;
    let cancelled = false;
    s.set({ loading: true, error: null });
    marketApi
      .query(s.sessionId, {
        filters: {
          products: s.filterProducts.length ? s.filterProducts : undefined,
          days: s.filterDays.length ? s.filterDays : undefined,
          ts_range: s.filterTsRange ?? undefined,
        },
        series: [...SERIES],
        downsample: { target_points: 6000, method: "lttb" },
      })
      .then((q) => !cancelled && s.set({ query: q, loading: false }))
      .catch((e) => !cancelled && s.set({ error: (e as Error).message, loading: false }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.sessionId, s.filterProducts, s.filterDays, s.filterTsRange]);

  if (!s.meta) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Filters</CardTitle>
        <span className="text-xs text-muted">
          {s.query ? `${s.query.original_points.toLocaleString()} pts → downsampled` : s.loading ? "loading…" : ""}
        </span>
      </CardHeader>
      <CardBody className="space-y-3">
        <div>
          <p className="text-xs text-muted mb-1">Products</p>
          <MultiSelect
            options={s.meta.products}
            value={s.filterProducts}
            onChange={(v) => s.set({ filterProducts: v as string[] })}
          />
        </div>
        <div>
          <p className="text-xs text-muted mb-1">Days</p>
          <MultiSelect
            options={s.meta.days}
            value={s.filterDays}
            onChange={(v) => s.set({ filterDays: v as number[] })}
          />
        </div>
        {s.meta.timestamp_range && (
          <div>
            <p className="text-xs text-muted mb-1">Timestamp range</p>
            <div className="flex gap-2 items-center">
              <Input
                type="number"
                placeholder={String(s.meta.timestamp_range[0])}
                value={s.filterTsRange?.[0] ?? ""}
                onChange={(e) => {
                  const lo = e.target.value === "" ? null : Number(e.target.value);
                  const hi = s.filterTsRange?.[1] ?? s.meta!.timestamp_range![1];
                  s.set({ filterTsRange: lo == null ? null : [lo, hi] });
                }}
              />
              <span className="text-muted">—</span>
              <Input
                type="number"
                placeholder={String(s.meta.timestamp_range[1])}
                value={s.filterTsRange?.[1] ?? ""}
                onChange={(e) => {
                  const hi = e.target.value === "" ? null : Number(e.target.value);
                  const lo = s.filterTsRange?.[0] ?? s.meta!.timestamp_range![0];
                  s.set({ filterTsRange: hi == null ? null : [lo, hi] });
                }}
              />
            </div>
          </div>
        )}
        {s.error && <p className="text-sm text-bear">{s.error}</p>}
      </CardBody>
    </Card>
  );
}
