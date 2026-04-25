type Props = {
  label: string;
  value: string;
  sub?: string;
  tone?: "neutral" | "positive" | "negative";
};

export function MetricCard({ label, value, sub, tone = "neutral" }: Props) {
  const valueColor =
    tone === "positive"
      ? "text-emerald-400"
      : tone === "negative"
        ? "text-rose-400"
        : "text-neutral-100";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`mt-1 text-xl font-semibold tabular-nums ${valueColor}`}>{value}</div>
      {sub ? <div className="mt-0.5 text-xs text-neutral-500 tabular-nums">{sub}</div> : null}
    </div>
  );
}
