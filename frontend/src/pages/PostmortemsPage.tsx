import { useApi } from "../hooks/useApi";
import { api } from "../api/client";
import { SectionCard } from "../components/SectionCard";
import { EmptyState } from "../components/EmptyState";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusPill } from "../components/StatusPill";

const usd = (value: number) =>
  value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

export function PostmortemsPage() {
  const { data, loading, error } = useApi(() => api.postmortems(), []);

  if (loading) return <LoadingBlock />;
  if (error) return <EmptyState title="Couldn't load reviews" hint={error} />;
  if (!data || data.length === 0) return <EmptyState title="No reviews yet" />;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {data.map((postmortem) => {
        const pnlTone = postmortem.pnl >= 0 ? "positive" : "negative";
        const drivers = Object.entries(postmortem.feature_drivers_json || {})
          .sort((left, right) => Math.abs(right[1]) - Math.abs(left[1]))
          .slice(0, 6);

        return (
          <SectionCard key={postmortem.id}>
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-neutral-100">
                    {postmortem.market_question}
                  </div>
                  <div className="text-xs text-neutral-500">
                    {new Date(postmortem.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill tone={pnlTone}>{usd(postmortem.pnl)}</StatusPill>
                  <StatusPill>{postmortem.final_result}</StatusPill>
                </div>
              </div>

              {postmortem.summary ? (
                <p className="text-sm leading-relaxed text-neutral-300">{postmortem.summary}</p>
              ) : null}

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <Block label="Sizing" text={postmortem.sizing_assessment} />
                <Block label="Lessons" text={postmortem.lessons_learned} />
              </div>

              {drivers.length > 0 ? (
                <div>
                  <div className="mb-1 text-[10px] uppercase tracking-wide text-neutral-500">
                    Feature drivers
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {drivers.map(([key, value]) => (
                      <StatusPill key={key} tone={value >= 0 ? "positive" : "negative"}>
                        {key} {value >= 0 ? "+" : ""}
                        {value.toFixed(2)}
                      </StatusPill>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </SectionCard>
        );
      })}
    </div>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  if (!text) return null;

  return (
    <div className="rounded bg-neutral-950/60 p-2">
      <div className="text-[10px] uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-0.5 text-xs text-neutral-300">{text}</div>
    </div>
  );
}
