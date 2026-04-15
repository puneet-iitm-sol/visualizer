"use client";
import { UploadPanel } from "./_components/upload-panel";
import { FilterPanel } from "./_components/filter-panel";
import { PriceChart } from "./_components/price-chart";
import { OrderBookDepth } from "./_components/orderbook-depth";
import { MultiLineChart } from "./_components/multi-line-chart";
import { MicrostructurePanel } from "./_components/microstructure-panel";
import { useMarketStore } from "@/lib/store/market-store";

const GROUP = "market";

export default function MarketDataPage() {
  const { sessionId, query, selected } = useMarketStore();

  return (
    <div className="grid grid-cols-12 gap-3">
      <aside className="col-span-12 lg:col-span-3 space-y-3">
        <UploadPanel />
        {sessionId && <FilterPanel />}
      </aside>

      <section className={`col-span-12 ${selected ? "lg:col-span-6" : "lg:col-span-9"} space-y-3`}>
        {!sessionId ? (
          <div className="rounded-lg border border-border bg-panel p-10 text-center text-muted">
            Upload a Prosperity CSV pair to begin.
          </div>
        ) : !query ? (
          <div className="rounded-lg border border-border bg-panel p-10 text-center text-muted">
            Loading series…
          </div>
        ) : (
          <>
            <PriceChart group={GROUP} />
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              <OrderBookDepth group={GROUP} />
              <MultiLineChart title="Volume per tick" group={GROUP} payload={query.series.volume} asBar height={220} />
              <MultiLineChart title="Spread (ask₁ − bid₁)" group={GROUP} payload={query.series.spread} height={220} />
              <MultiLineChart title="Cumulative PnL" group={GROUP} payload={query.series.pnl} totalKey="__total__" height={220} />
              <MultiLineChart title="Microprice" group={GROUP} payload={query.series.microprice} height={220} />
              <MultiLineChart title="WOBI (3 levels)" group={GROUP} payload={query.series.wobi} height={220} />
            </div>
          </>
        )}
      </section>

      {selected && (
        <aside className="col-span-12 lg:col-span-3">
          <MicrostructurePanel />
        </aside>
      )}
    </div>
  );
}
