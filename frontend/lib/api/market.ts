import { api } from "./client";
import type {
  Filters,
  MarketMeta,
  MarketUploadResult,
  QueryResponse,
  SeriesKind,
  SnapshotResponse,
} from "@/lib/types/market";

export const marketApi = {
  newSession: () => api.post<{ session_id: string }>("/api/market/sessions"),
  upload: (sid: string, files: File[]) =>
    api.upload<MarketUploadResult>(`/api/market/sessions/${sid}/upload`, files),
  meta: (sid: string) => api.get<MarketMeta>(`/api/market/sessions/${sid}/meta`),
  query: (
    sid: string,
    body: { filters?: Filters; series: SeriesKind[]; downsample?: { target_points: number; method: "lttb" | "bucket" } },
  ) => api.post<QueryResponse>(`/api/market/sessions/${sid}/query`, body),
  snapshot: (sid: string, params: { ts: number; product: string; day?: number; context?: number }) => {
    const qs = new URLSearchParams();
    qs.set("ts", String(params.ts));
    qs.set("product", params.product);
    if (params.day != null) qs.set("day", String(params.day));
    if (params.context != null) qs.set("context", String(params.context));
    return api.get<SnapshotResponse>(`/api/market/sessions/${sid}/snapshot?${qs}`);
  },
};
