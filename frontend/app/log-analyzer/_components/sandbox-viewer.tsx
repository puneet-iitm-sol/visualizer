"use client";
import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogStore } from "@/lib/store/log-store";
import { logsApi } from "@/lib/api/logs";
import type { SandboxRow } from "@/lib/types/log";
import { fmtTs } from "@/lib/utils/format";

export function SandboxViewer() {
  const { sessionId } = useLogStore();
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<SandboxRow[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    setBusy(true);
    const id = setTimeout(() => {
      logsApi
        .sandbox(sessionId, { q: q || undefined, limit: 500 })
        .then((r) => { setRows(r.rows); setTotal(r.total); })
        .finally(() => setBusy(false));
    }, 250);
    return () => clearTimeout(id);
  }, [sessionId, q]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sandbox logs ({total.toLocaleString()})</CardTitle>
        <Input
          placeholder="filter…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-48"
        />
      </CardHeader>
      <CardBody className="p-0">
        <div className="max-h-96 overflow-auto text-xs font-mono">
          {busy && <p className="p-3 text-muted">Loading…</p>}
          {rows.length === 0 && !busy && <p className="p-3 text-muted">No matches.</p>}
          <table className="w-full">
            <tbody>
              {rows.map((r) => (
                <tr key={r.line_no} className="border-b border-border/50 hover:bg-bg/40">
                  <td className="px-2 py-1 text-muted whitespace-nowrap w-20">{r.timestamp != null ? fmtTs(r.timestamp) : `#${r.line_no}`}</td>
                  <td className="px-2 py-1 text-accent2 whitespace-nowrap w-12">{r.level ?? ""}</td>
                  <td className="px-2 py-1 text-accent whitespace-nowrap w-32">{r.product_tag ?? ""}</td>
                  <td className="px-2 py-1 break-all">{r.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}
