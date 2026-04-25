import { useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { LoadingBlock } from "../components/LoadingBlock";
import { SectionCard } from "../components/SectionCard";
import { StatusPill } from "../components/StatusPill";
import { useApi } from "../hooks/useApi";
import type { Signal, Trade } from "../types/api";

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const usd = (value: number) =>
  value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

const reasonText: Record<string, string> = {
  approved: "All risk checks passed.",
  confidence_below_threshold: "The model was not confident enough.",
  edge_too_small: "The price gap was too small to justify a trade.",
  max_open_trades_reached: "The agent already has enough open trades.",
  max_daily_loss_reached: "The daily loss limit was already reached.",
  position_size_cap_exceeded: "The trade size would have been too large.",
  market_exposure_cap_exceeded: "There was already too much exposure on this market.",
  category_exposure_cap_exceeded: "There was already too much exposure in this sport.",
  non_positive_stake: "The sizing logic produced no usable trade size.",
  insufficient_cash: "There was not enough cash left in the paper account.",
};

type Filter = "all" | "accepted" | "skipped";

type AcceptedIdea = {
  kind: "accepted";
  id: string;
  marketQuestion: string;
  marketUrl: string | null | undefined;
  eventTitle: string | null;
  marketProbability: number | null;
  fairProbability: number | null;
  edge: number;
  confidence: number;
  stake: number;
  rationale: string;
  summary: string;
};

type SkippedIdea = {
  kind: "skipped";
  id: string;
  marketQuestion: string;
  eventTitle: string | null;
  marketProbability: number;
  fairProbability: number;
  edge: number;
  confidence: number;
  stake: number;
  rationale: string;
  summary: string;
  reasonCodes: string[];
  mode: string;
  evProxy: number;
};

type IdeaCard = AcceptedIdea | SkippedIdea;

function explainSkipped(signal: Signal) {
  const reasons = signal.risk?.reason_codes ?? [];

  if (reasons.length === 0) {
    return "Skipped because the trade did not clear the current checks.";
  }

  const readable = reasons.map((code) => reasonText[code] ?? code.replace(/_/g, " "));
  return `Skipped because ${readable[0].charAt(0).toLowerCase()}${readable[0].slice(1)}`;
}

function explainAccepted(trade: Trade) {
  return `Accepted because the model thought this market was priced a bit too low, the edge looked strong enough, and the trade still fit the bankroll rules. Planned stake: ${usd(trade.stake)}.`;
}

export function CandidatesPage() {
  const {
    data: signals,
    loading: loadingSignals,
    error: signalsError,
  } = useApi(() => api.signals(), []);
  const {
    data: trades,
    loading: loadingTrades,
    error: tradesError,
  } = useApi(() => api.trades(), []);
  const [filter, setFilter] = useState<Filter>("all");

  const acceptedIdeas = useMemo<AcceptedIdea[]>(() => {
    if (!trades) return [];
    return trades.map((trade) => ({
      kind: "accepted",
      id: `trade-${trade.id}`,
      marketQuestion: trade.market_question,
      marketUrl: trade.market_url,
      eventTitle: null,
      marketProbability: null,
      fairProbability: null,
      edge: trade.entry_edge,
      confidence: trade.confidence,
      stake: trade.stake,
      rationale: trade.rationale,
      summary: explainAccepted(trade),
    }));
  }, [trades]);

  const skippedIdeas = useMemo<SkippedIdea[]>(() => {
    if (!signals) return [];
    return signals
      .filter((signal) => !signal.risk?.approved)
      .map((signal) => ({
        kind: "skipped",
        id: `signal-${signal.id}`,
        marketQuestion: signal.market_question,
        marketUrl: null,
        eventTitle: signal.event_title,
        marketProbability: signal.market_probability,
        fairProbability: signal.fair_probability,
        edge: signal.edge,
        confidence: signal.confidence,
        stake: signal.risk?.proposed_stake ?? 0,
        rationale: signal.rationale,
        summary: explainSkipped(signal),
        reasonCodes: signal.risk?.reason_codes ?? [],
        mode: signal.mode,
        evProxy: signal.expected_value_proxy,
      }));
  }, [signals]);

  const ideas = useMemo<IdeaCard[]>(() => {
    if (filter === "accepted") return acceptedIdeas;
    if (filter === "skipped") return skippedIdeas;
    return [...acceptedIdeas, ...skippedIdeas];
  }, [acceptedIdeas, skippedIdeas, filter]);

  if (loadingSignals || loadingTrades) return <LoadingBlock />;
  if (signalsError || tradesError) {
    return (
      <EmptyState
        title="Couldn't load trade ideas"
        hint={signalsError ?? tradesError ?? "Unknown error"}
      />
    );
  }

  if (acceptedIdeas.length === 0 && skippedIdeas.length === 0) {
    return <EmptyState title="No trade ideas" hint="Run the agent to scan." />;
  }

  return (
    <SectionCard
      title="Trade Ideas"
      action={
        <div className="flex gap-1 rounded-md bg-neutral-900 p-0.5 text-xs">
          {(["all", "accepted", "skipped"] as Filter[]).map((value) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`rounded px-2 py-1 capitalize transition ${
                filter === value
                  ? "bg-neutral-700 text-neutral-100"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {value}
            </button>
          ))}
        </div>
      }
    >
      {ideas.length === 0 ? (
        <EmptyState title="No trade ideas" hint={`No ${filter} ideas right now.`} />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {ideas.map((idea) => {
            const approved = idea.kind === "accepted";
            const edgeTone = idea.edge >= 0 ? "positive" : "negative";

            return (
              <div
                key={idea.id}
                className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-neutral-100">
                        {idea.marketQuestion}
                      </div>
                      {idea.eventTitle ? (
                        <div className="truncate text-xs text-neutral-500">{idea.eventTitle}</div>
                      ) : null}
                      {approved && idea.marketUrl ? (
                        <a
                          href={idea.marketUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex text-xs font-medium text-emerald-400 hover:text-emerald-300"
                        >
                          View on Polymarket
                        </a>
                      ) : null}
                    </div>
                    <StatusPill tone={approved ? "positive" : "warning"}>
                      {approved ? "trade placed" : "skipped"}
                    </StatusPill>
                  </div>

                  <div
                    className={`rounded-lg border p-3 ${
                      approved
                        ? "border-emerald-900/80 bg-emerald-950/30"
                        : "border-amber-900/80 bg-amber-950/20"
                    }`}
                  >
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
                      Why This Was {approved ? "Accepted" : "Skipped"}
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-neutral-200">
                      {idea.summary}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
                    {idea.marketProbability !== null ? (
                      <Field label="Market p" value={pct(idea.marketProbability)} />
                    ) : (
                      <Field label="Market p" value="—" />
                    )}
                    {idea.fairProbability !== null ? (
                      <Field label="Fair p" value={pct(idea.fairProbability)} />
                    ) : (
                      <Field label="Fair p" value="—" />
                    )}
                    <Field label="Edge" value={pct(idea.edge)} tone={edgeTone} />
                    <Field label="Confidence" value={pct(idea.confidence)} />
                    {"mode" in idea ? <Field label="Mode" value={idea.mode} /> : <Field label="Mode" value="traded" />}
                    {"evProxy" in idea ? (
                      <Field label="EV proxy" value={idea.evProxy.toFixed(3)} />
                    ) : (
                      <Field label="EV proxy" value="—" />
                    )}
                    <Field label="Stake" value={usd(idea.stake)} />
                    <Field label="Status" value={approved ? "placed" : "skipped"} />
                  </div>

                  {"reasonCodes" in idea && idea.reasonCodes.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {idea.reasonCodes.map((code) => (
                        <StatusPill key={code} tone="neutral">
                          {reasonText[code] ?? code.replace(/_/g, " ")}
                        </StatusPill>
                      ))}
                    </div>
                  ) : null}

                  {idea.rationale ? (
                    <p className="line-clamp-3 rounded bg-neutral-950/60 p-2 text-xs leading-relaxed text-neutral-400">
                      {idea.rationale}
                    </p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

function Field({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
}) {
  const color =
    tone === "positive"
      ? "text-emerald-400"
      : tone === "negative"
        ? "text-rose-400"
        : "text-neutral-200";

  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`tabular-nums ${color}`}>{value}</div>
    </div>
  );
}
