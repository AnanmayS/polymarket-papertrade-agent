import { useState } from "react";
import { api } from "../api/client";

type Props = {
  onRan?: () => void;
};

export function EngineControls({ onRan }: Props) {
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    setStatus(null);

    try {
      const result = await api.runCycle();
      setStatus(result?.message || result?.status || "Cycle complete");
      onRan?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      {status ? <span className="text-xs text-emerald-400">{status}</span> : null}
      {error ? <span className="text-xs text-rose-400">{error}</span> : null}
      <button
        onClick={run}
        disabled={running}
        className="inline-flex items-center rounded-md bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-neutral-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {running ? "Running..." : "Run Agent"}
      </button>
    </div>
  );
}
