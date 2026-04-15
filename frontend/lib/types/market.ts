export type SeriesKind =
  | "mid" | "bid_1" | "ask_1" | "spread" | "volume" | "pnl" | "depth" | "trades"
  | "microprice" | "wobi" | "ema" | "sma" | "zscore" | "vwap";

export interface Filters {
  products?: string[];
  days?: number[];
  ts_range?: [number, number];
  pnl_min?: number | null;
  pnl_max?: number | null;
}

export interface UploadReportFile {
  name: string;
  kind: "prices" | "trades";
  round: number | null;
  day: number | null;
  rows: number;
  columns: string[];
  errors: string[];
}

export interface MarketUploadResult {
  files: UploadReportFile[];
  products: string[];
  days: number[];
  timestamp_range: [number, number] | null;
}

export interface MarketMeta {
  products: string[];
  days: number[];
  timestamp_range: [number, number] | null;
  has_prices: boolean;
  has_trades: boolean;
}

export interface TradeMarker {
  ts: number;
  px: number;
  qty: number;
  buyer?: string | null;
  seller?: string | null;
}

export type SeriesPayload = {
  __x__?: number[];
  [product: string]: number[] | undefined;
};

export interface DepthPayload {
  bid: number[][];
  ask: number[][];
  __x__: number[];
}

export interface QueryResponse {
  x: number[];
  series: {
    mid?: SeriesPayload;
    bid_1?: SeriesPayload;
    ask_1?: SeriesPayload;
    spread?: SeriesPayload;
    volume?: SeriesPayload;
    pnl?: SeriesPayload & { __total__?: number[] };
    depth?: Record<string, DepthPayload>;
    trades?: Record<string, TradeMarker[]>;
    microprice?: SeriesPayload;
    wobi?: SeriesPayload;
    ema?: SeriesPayload;
    sma?: SeriesPayload;
    zscore?: SeriesPayload;
    vwap?: SeriesPayload;
  };
  downsampled: boolean;
  original_points: number;
}

export interface SnapshotResponse {
  timestamp: number;
  product: string;
  day?: number;
  book: { bids: [number, number][]; asks: [number, number][] } | null;
  trades_at_ts: TradeMarker[];
  metrics: Record<string, number | null | undefined>;
  context: Array<{
    timestamp: number;
    mid_price: number;
    spread: number;
    trade_volume: number;
    microprice?: number | null;
    wobi?: number | null;
  }>;
}
