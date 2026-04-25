type Tone = "neutral" | "positive" | "negative" | "warning" | "info";

const tones: Record<Tone, string> = {
  neutral: "bg-neutral-800 text-neutral-300 ring-neutral-700",
  positive: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
  negative: "bg-rose-500/10 text-rose-400 ring-rose-500/20",
  warning: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
  info: "bg-sky-500/10 text-sky-400 ring-sky-500/20",
};

export function StatusPill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
