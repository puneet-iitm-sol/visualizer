"use client";
import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileDrop } from "@/components/ui/file-drop";
import { useLogStore } from "@/lib/store/log-store";
import { logsApi } from "@/lib/api/logs";
import type { LogFileReport } from "@/lib/types/log";
import { CheckCircle, AlertCircle, XCircle } from "lucide-react";

export function LogUpload() {
  const { sessionId, set } = useLogStore();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reports, setReports] = useState<LogFileReport[] | null>(null);

  const handle = async (files: File[]) => {
    setBusy(true);
    setErr(null);
    setReports(null);
    try {
      let sid = sessionId;
      if (!sid) {
        const res = await logsApi.newSession();
        sid = res.session_id;
      }
      const uploadResult = await logsApi.upload(sid, files);
      setReports(uploadResult.files);

      const meta = await logsApi.meta(sid);
      const dashboard = await logsApi.dashboard(sid);
      set({ sessionId: sid, meta, dashboard, state: null });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleCompare = async (files: File[]) => {
    setBusy(true);
    setErr(null);
    try {
      const res = await logsApi.newSession();
      await logsApi.upload(res.session_id, files);
      set({ compareSessionId: res.session_id });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload submission `.log`</CardTitle>
        {sessionId && (
          <Button size="sm" variant="ghost" onClick={() => { useLogStore.getState().reset(); setReports(null); }}>
            Reset
          </Button>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        <FileDrop
          accept=".log,.txt,text/plain"
          label={busy ? "Uploading…" : "Drop submission .log file here"}
          onFiles={handle}
        />

        {err && (
          <div className="flex items-start gap-2 rounded-md border border-bear/40 bg-bear/10 p-2">
            <XCircle className="h-4 w-4 text-bear shrink-0 mt-0.5" />
            <p className="text-xs text-bear break-all">{err}</p>
          </div>
        )}

        {reports && reports.map((r, i) => (
          <div key={i} className="rounded-md border border-border bg-bg p-2 space-y-1">
            <div className="flex items-center gap-2">
              {r.parse_errors.length === 0
                ? <CheckCircle className="h-3.5 w-3.5 text-bull shrink-0" />
                : <AlertCircle className="h-3.5 w-3.5 text-accent shrink-0" />}
              <span className="text-xs font-mono text-text truncate">{r.name}</span>
            </div>
            <div className="text-xs text-muted font-mono pl-5 space-y-0.5">
              <div>sections: {r.sections_found.length
                ? r.sections_found.join(", ")
                : <span className="text-bear">none detected</span>}
              </div>
              {r.sections_found.includes("activities") && (
                <div>activities: {r.activities_rows.toLocaleString()} rows</div>
              )}
              {r.sections_found.includes("trade_history") && (
                <div>trade history: {r.trade_history_rows.toLocaleString()} rows</div>
              )}
              {r.sections_found.includes("sandbox") && (
                <div>sandbox: {r.sandbox_lines.toLocaleString()} lines</div>
              )}
              {r.parse_errors.map((e, j) => (
                <div key={j} className="text-bear">⚠ {e.reason}</div>
              ))}
            </div>
          </div>
        ))}

        {sessionId && (
          <div className="pt-1 border-t border-border">
            <p className="text-xs text-muted mb-2">Compare with a 2nd submission:</p>
            <FileDrop
              accept=".log,.txt"
              multiple={false}
              label="Drop a 2nd .log to overlay"
              onFiles={handleCompare}
            />
          </div>
        )}
      </CardBody>
    </Card>
  );
}
