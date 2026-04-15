"use client";
import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { FileDrop } from "@/components/ui/file-drop";
import { Button } from "@/components/ui/button";
import { useMarketStore } from "@/lib/store/market-store";
import { marketApi } from "@/lib/api/market";

export function UploadPanel() {
  const { sessionId, set } = useMarketStore();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [report, setReport] = useState<{ name: string; rows: number; kind: string }[] | null>(null);

  const handle = async (files: File[]) => {
    setBusy(true);
    setErr(null);
    try {
      let sid = sessionId;
      if (!sid) {
        const res = await marketApi.newSession();
        sid = res.session_id;
      }
      const result = await marketApi.upload(sid, files);
      const meta = await marketApi.meta(sid);
      set({ sessionId: sid, meta, query: null, selected: null });
      setReport(result.files.map((f) => ({ name: f.name, rows: f.rows, kind: f.kind })));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Prosperity CSVs</CardTitle>
        {sessionId && (
          <Button size="sm" variant="ghost" onClick={() => useMarketStore.getState().reset()}>
            Reset
          </Button>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        <FileDrop
          accept=".csv,text/csv"
          label={busy ? "Uploading…" : "Drop prices_round_*.csv + trades_round_*.csv"}
          onFiles={handle}
        />
        {err && <p className="text-sm text-bear">{err}</p>}
        {report && (
          <ul className="text-xs text-muted font-mono space-y-1 max-h-32 overflow-auto">
            {report.map((r, i) => (
              <li key={i}>
                <span className="text-text">{r.name}</span> · {r.kind} · {r.rows.toLocaleString()} rows
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
