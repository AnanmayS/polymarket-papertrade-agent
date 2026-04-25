import { useMemo, useState } from "react";
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
const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

function acceptedSummary(trade: {
  entry_edge: number;
  confidence: number;
  stake: number;
}) {
  return `Accepted with ${pct(trade.entry_edge)} edge, ${pct(trade.confidence)} confidence, and ${usd(trade.stake)} planned stake.`;
}

type Filter = "all" | "open" | "settled";

export function TradesPage() {
  const { data, loading, error } = useApi(() => api.trades(), []);
  const [filter, setFilter] = useState<Filter>("all");

  const trades = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data;
    if (filter === "open") return data.filter((trade) => !trade.settled_at);
    return data.filter((trade) => Boolean(trade.settled_at));
  }, [data, filter]);

  return (
    <SectionCard
      title="Paper trades"
      action={
        <div className="flex gap-1 rounded-md bg-neutral-900 p-0.5 text-xs">
          {(["all", "open", "settled"] as Filter[]).map((value) => (
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
      {loading ? (
        <LoadingBlock />
      ) : error ? (
        <EmptyState title="Couldn't load trades" hint={error} />
      ) : trades.length === 0 ? (
        <EmptyState title="No trades" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <Th>Market</Th>
                <Th>Side</Th>
                <Th>Status</Th>
                <Th align="right">Stake</Th>
                <Th align="right">Fill</Th>
                <Th align="right">Conf</Th>
                <Th align="right">Costs</Th>
                <Th align="right">PnL</Th>
                <Th>Opened</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {trades.map((trade) => {
                const pnl = trade.realized_pnl + trade.unrealized_pnl;
                const costs = trade.fees_paid + trade.slippage_paid;
                const sideLabel =
                  trade.side === "buy_yes"
                    ? "yes"
                    : trade.side === "buy_no"
                      ? "no"
                      : trade.side;
                const sideTone =
                  sideLabel === "yes" ? "positive" : sideLabel === "no" ? "info" : "neutral";

                return (
                  <tr key={trade.id} className="hover:bg-neutral-900/50">
                    <Td className="max-w-sm">
                      <div className="truncate text-neutral-100">{trade.market_question}</div>
                      {trade.market_url ? (
                        <a
                          href={trade.market_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex text-xs font-medium text-emerald-400 hover:text-emerald-300"
                        >
                          View on Polymarket
                        </a>
                      ) : null}
                      <div className="mt-1 text-xs text-neutral-500">
                        {acceptedSummary(trade)}
                      </div>
                    </Td>
                    <Td>
                      <StatusPill tone={sideTone}>{sideLabel}</StatusPill>
                    </Td>
                    <Td>
                      <StatusPill tone={trade.settled_at ? "neutral" : "info"}>
                        {trade.status}
                      </StatusPill>
                    </Td>
                    <Td align="right">{usd(trade.stake)}</Td>
                    <Td align="right">{trade.fill_price.toFixed(3)}</Td>
                    <Td align="right">{pct(trade.confidence)}</Td>
                    <Td align="right" className="text-neutral-400">
                      {usd(costs)}
                    </Td>
                    <Td
                      align="right"
                      className={pnl >= 0 ? "text-emerald-400" : "text-rose-400"}
                    >
                      {usd(pnl)}
                    </Td>
                    <Td className="text-neutral-400">
                      {trade.opened_at ? new Date(trade.opened_at).toLocaleString() : "—"}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}

function Th({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return <th className={`px-3 py-2 ${align === "right" ? "text-right" : "text-left"}`}>{children}</th>;
}

function Td({
  children,
  align = "left",
  className = "",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
  className?: string;
}) {
  return (
    <td
      className={`px-3 py-2 tabular-nums ${
        align === "right" ? "text-right" : "text-left"
      } ${className}`}
    >
      {children}
    </td>
  );
}
