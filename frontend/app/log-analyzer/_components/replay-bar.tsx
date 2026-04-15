"use client";
import { useEffect, useRef } from "react";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLogStore } from "@/lib/store/log-store";
import { logsApi } from "@/lib/api/logs";
import { fmtTs } from "@/lib/utils/format";
import { Pause, Play, SkipBack, SkipForward, Square } from "lucide-react";

const SPEEDS = [1000, 500, 250, 100, 50];

export function ReplayBar() {
  const { sessionId, replay, setReplay } = useLogStore();
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const step = async (direction: -1 | 0 | 1) => {
    if (!sessionId) return;
    const r = await logsApi.replay(sessionId, replay.ts, direction);
    if (r.ts == null) {
      setReplay({ playing: false });
      return;
    }
    setReplay({ ts: r.ts });
  };

  useEffect(() => {
    if (replay.playing) {
      timer.current = setInterval(() => step(1), replay.speedMs);
    }
    return () => {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replay.playing, replay.speedMs, sessionId, replay.ts]);

  return (
    <Card>
      <CardBody className="flex items-center gap-3 py-2">
        <Button size="icon" variant="ghost" onClick={() => step(-1)} disabled={!sessionId}>
          <SkipBack className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          variant={replay.playing ? "default" : "outline"}
          onClick={() => setReplay({ playing: !replay.playing })}
          disabled={!sessionId}
        >
          {replay.playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <Button size="icon" variant="ghost" onClick={() => step(1)} disabled={!sessionId}>
          <SkipForward className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={() => setReplay({ ts: null, playing: false })}
          disabled={!sessionId}
        >
          <Square className="h-4 w-4" />
        </Button>
        <div className="text-sm font-mono ml-2">ts {replay.ts != null ? fmtTs(replay.ts) : "—"}</div>
        <div className="ml-auto flex items-center gap-1 text-xs text-muted">
          <span>speed</span>
          {SPEEDS.map((ms) => (
            <button
              key={ms}
              onClick={() => setReplay({ speedMs: ms })}
              className={`rounded px-2 h-6 ${
                replay.speedMs === ms ? "bg-accent/20 text-accent" : "hover:text-text"
              }`}
            >
              {1000 / ms}×
            </button>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}
