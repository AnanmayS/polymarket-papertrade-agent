import { useMemo, useState } from "react";
import { useApi } from "../hooks/useApi";
import { api } from "../api/client";
import { SectionCard } from "../components/SectionCard";
import { EmptyState } from "../components/EmptyState";
import { LoadingBlock } from "../components/LoadingBlock";

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const num = (value: number) =>
  value >= 1_000_000
    ? `${(value / 1_000_000).toFixed(1)}M`
    : value >= 1_000
      ? `${(value / 1_000).toFixed(1)}k`
      : value.toFixed(0);

export function ScannerPage() {
  const { data, loading, error } = useApi(() => api.markets(), []);
  const [league, setLeague] = useState("");

  const filtered = useMemo(() => {
    if (!data) return [];
    const query = league.trim().toLowerCase();
    if (!query) return data;
    return data.filter((market) =>
      (market.sports_league || "").toLowerCase().includes(query),
    );
  }, [data, league]);

  return (
    <SectionCard
      title="Active markets"
      action={
        <input
          value={league}
          onChange={(event) => setLeague(event.target.value)}
          placeholder="Filter by league"
          className="w-44 rounded-md border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
        />
      }
    >
      {loading ? (
        <LoadingBlock />
      ) : error ? (
        <EmptyState title="Couldn't load markets" hint={error} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No markets" hint={league ? "Try clearing the filter." : undefined} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <Th>Market</Th>
                <Th>League</Th>
                <Th align="right">Implied</Th>
                <Th align="right">Spread</Th>
                <Th align="right">Liquidity</Th>
                <Th align="right">Volume</Th>
                <Th>Resolution</Th>
                <Th align="right">Score</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {filtered.map((market) => (
                <tr key={market.id} className="hover:bg-neutral-900/50">
                  <Td className="max-w-sm truncate text-neutral-100">{market.question}</Td>
                  <Td className="text-neutral-400">{market.sports_league || "—"}</Td>
                  <Td align="right">{pct(market.implied_probability)}</Td>
                  <Td align="right">{market.spread.toFixed(3)}</Td>
                  <Td align="right">{num(market.liquidity)}</Td>
                  <Td align="right">{num(market.volume)}</Td>
                  <Td className="text-neutral-400">
                    {market.resolution_time
                      ? new Date(market.resolution_time).toLocaleDateString()
                      : "—"}
                  </Td>
                  <Td align="right" className="text-emerald-400">
                    {market.opportunity_score.toFixed(2)}
                  </Td>
                </tr>
              ))}
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
