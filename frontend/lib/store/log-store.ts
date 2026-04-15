"use client";
import { create } from "zustand";
import type { DashboardResponse, LogMeta, StateResponse } from "@/lib/types/log";

interface LogState {
  sessionId: string | null;
  compareSessionId: string | null;
  meta: LogMeta | null;

  filterProducts: string[];
  filterTsRange: [number, number] | null;

  dashboard: DashboardResponse | null;
  state: StateResponse | null;

  replay: { ts: number | null; playing: boolean; speedMs: number };
  loading: boolean;
  error: string | null;

  set: (patch: Partial<LogState>) => void;
  setReplay: (patch: Partial<LogState["replay"]>) => void;
  reset: () => void;
}

const initial: Omit<LogState, "set" | "setReplay" | "reset"> = {
  sessionId: null,
  compareSessionId: null,
  meta: null,
  filterProducts: [],
  filterTsRange: null,
  dashboard: null,
  state: null,
  replay: { ts: null, playing: false, speedMs: 250 },
  loading: false,
  error: null,
};

export const useLogStore = create<LogState>((set, get) => ({
  ...initial,
  set: (patch) => set(patch),
  setReplay: (patch) => set({ replay: { ...get().replay, ...patch } }),
  reset: () => set(initial),
}));
