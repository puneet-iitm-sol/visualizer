export interface LogFileReport {
  name: string;
  sections_found: string[];
  sandbox_lines: number;
  activities_rows: number;
  trade_history_rows: number;
  parse_errors: Array<{ file?: string; line?: number; reason: string }>;
}

export interface LogUploadResult {
  files: LogFileReport[];
  products: string[];
  timestamp_range: [number, number] | null;
  sandbox_lines: number;
  activities_rows: number;
  trade_history_rows: number;
}

export interface LogMeta extends LogUploadResult {
  has_activities: boolean;
  has_trade_history: boolean;
  has_sandbox: boolean;
}

export interface PnlSeries {
  __x__?: number[];
  __total__?: number[];
  [product: string]: number[] | undefined;
}

export interface PositionSeries {
  [product: string]: { x: number[]; y: number[] };
}

export interface DashboardResponse {
  x: number[];
  algo_pnl: PnlSeries;
  position: PositionSeries;
  executions: Record<string, Array<{ ts: number; px: number; qty: number; buyer?: string; seller?: string }>>;
}

export interface SandboxRow {
  line_no: number;
  timestamp: number | null;
  level: string | null;
  product_tag: string | null;
  text: string;
}

export interface StateResponse {
  timestamp: number;
  positions: Record<string, number>;
  fills_at_tick: Array<{ timestamp: number; symbol: string; price: number; quantity: number; buyer?: string; seller?: string }>;
  sandbox_window: SandboxRow[];
  metrics: Record<string, { mid_price: number; spread: number; pnl: number }>;
}

export interface ReplayResponse {
  ts: number | null;
  at_boundary?: boolean;
  positions?: Record<string, number>;
  fills_at_tick?: StateResponse["fills_at_tick"];
  sandbox_window?: SandboxRow[];
  metrics?: StateResponse["metrics"];
}

export interface CompareResponse {
  sids: string[];
  pnl: Record<string, { x: number[]; y: number[] }>;
  position: Record<string, Record<string, { x: number[]; y: number[] }>>;
  divergences: Array<{ ts: number; product: string; [sid: string]: number | string | null }>;
}
