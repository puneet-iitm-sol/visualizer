import { api } from "./client";
import type {
  CompareResponse,
  DashboardResponse,
  LogMeta,
  LogUploadResult,
  ReplayResponse,
  SandboxRow,
  StateResponse,
} from "@/lib/types/log";

export const logsApi = {
  newSession: () => api.post<{ session_id: string }>("/api/logs/sessions"),
  upload: (sid: string, files: File[]) =>
    api.upload<LogUploadResult>(`/api/logs/sessions/${sid}/upload`, files),
  meta: (sid: string) => api.get<LogMeta>(`/api/logs/sessions/${sid}/meta`),
  dashboard: (sid: string, body: { filters?: { products?: string[]; ts_range?: [number, number] }; target_points?: number } = {}) =>
    api.post<DashboardResponse>(`/api/logs/sessions/${sid}/dashboard`, body),
  state: (sid: string, ts: number) => api.get<StateResponse>(`/api/logs/sessions/${sid}/state?ts=${ts}`),
  sandbox: (sid: string, params: { q?: string; ts_from?: number; ts_to?: number; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.ts_from != null) qs.set("ts_from", String(params.ts_from));
    if (params.ts_to != null) qs.set("ts_to", String(params.ts_to));
    if (params.limit != null) qs.set("limit", String(params.limit));
    if (params.offset != null) qs.set("offset", String(params.offset));
    return api.get<{ rows: SandboxRow[]; total: number }>(`/api/logs/sessions/${sid}/sandbox?${qs}`);
  },
  replay: (sid: string, ts: number | null, direction: -1 | 0 | 1 = 0) => {
    const qs = new URLSearchParams();
    if (ts != null) qs.set("ts", String(ts));
    qs.set("direction", String(direction));
    return api.get<ReplayResponse>(`/api/logs/sessions/${sid}/replay?${qs}`);
  },
  compare: (session_ids: string[]) =>
    api.post<CompareResponse>("/api/logs/compare", { session_ids }),
};
