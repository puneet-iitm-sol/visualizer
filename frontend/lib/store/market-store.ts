"use client";
import { create } from "zustand";
import type { MarketMeta, QueryResponse } from "@/lib/types/market";

interface SelectedTick { ts: number; product: string; day?: number }

interface MarketState {
  sessionId: string | null;
  meta: MarketMeta | null;

  filterProducts: string[];      // empty = all
  filterDays: number[];          // empty = all
  filterTsRange: [number, number] | null;

  query: QueryResponse | null;
  loading: boolean;
  error: string | null;

  selected: SelectedTick | null;

  set: (patch: Partial<MarketState>) => void;
  reset: () => void;
}

const initial: Omit<MarketState, "set" | "reset"> = {
  sessionId: null,
  meta: null,
  filterProducts: [],
  filterDays: [],
  filterTsRange: null,
  query: null,
  loading: false,
  error: null,
  selected: null,
};

export const useMarketStore = create<MarketState>((set) => ({
  ...initial,
  set: (patch) => set(patch),
  reset: () => set(initial),
}));
