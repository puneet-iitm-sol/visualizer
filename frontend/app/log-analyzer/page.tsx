"use client";
import { LogUpload } from "./_components/log-upload";
import { AlgoPnl } from "./_components/algo-pnl";
import { PositionTracker } from "./_components/position-tracker";
import { SandboxViewer } from "./_components/sandbox-viewer";
import { StateInspector } from "./_components/state-inspector";
import { ReplayBar } from "./_components/replay-bar";
import { ComparePanel } from "./_components/compare-panel";
import { useLogStore } from "@/lib/store/log-store";

const GROUP = "log";

export default function LogAnalyzerPage() {
  const { sessionId, dashboard } = useLogStore();

  return (
    <div className="grid grid-cols-12 gap-3">
      <aside className="col-span-12 lg:col-span-3 space-y-3">
        <LogUpload />
      </aside>

      <section className="col-span-12 lg:col-span-6 space-y-3">
        {!sessionId ? (
          <div className="rounded-lg border border-border bg-panel p-10 text-center text-muted">
            Upload a Prosperity submission `.log` to begin.
          </div>
        ) : !dashboard ? (
          <div className="rounded-lg border border-border bg-panel p-10 text-center text-muted">
            Loading dashboard…
          </div>
        ) : (
          <>
            <ReplayBar />
            <AlgoPnl group={GROUP} />
            <PositionTracker group={GROUP} />
            <ComparePanel group={GROUP} />
            <SandboxViewer />
          </>
        )}
      </section>

      <aside className="col-span-12 lg:col-span-3">
        {sessionId && <StateInspector />}
      </aside>
    </div>
  );
}
