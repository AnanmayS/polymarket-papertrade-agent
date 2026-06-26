import { useMemo } from "react";
import { useApi } from "../hooks/useApi";
import { api } from "../api/client";
import { SectionCard } from "../components/SectionCard";
import { MetricCard } from "../components/MetricCard";
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
const num = (value: number) => {
  if (Math.abs(value) >= 1000) return value.toFixed(0);
  return value.toFixed(2);
};

export function AnalysisPage() {
  const { data, loading, error } = useApi(() => api.analysis(), []);

  if (loading) return <LoadingBlock />;
  if (error) return <EmptyState title="Couldn't load analysis" hint={error} />;
  if (!data) return <EmptyState title="No analysis data yet" hint="Run the agent to generate trades and postmortems." />;

  const csvExportUrl = api.exportCsv();

  return (
    <div className="space-y-6">
      {/* Per-strategy performance */}
      <SectionCard title="Per-strategy performance">
        {data.strategy_performance.length === 0 ? (
          <EmptyState title="No settled trades yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <Th>Mode</Th>
                  <Th align="right">Trades</Th>
                  <Th align="right">Wins</Th>
                  <Th align="right">Losses</Th>
                  <Th align="right">Win rate</Th>
                  <Th align="right">Realized PnL</Th>
                  <Th align="right">Avg edge</Th>
                  <Th align="right">Avg PnL/trade</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {data.strategy_performance.map((s) => (
                  <tr key={s.mode} className="hover:bg-neutral-900/50">
                    <Td>
                      <StatusPill tone="info">{s.mode}</StatusPill>
                    </Td>
                    <Td align="right">{s.trades}</Td>
                    <Td align="right" className="text-emerald-400">{s.wins}</Td>
                    <Td align="right" className="text-rose-400">{s.losses}</Td>
                    <Td align="right">{pct(s.win_rate)}</Td>
                    <Td
                      align="right"
                      className={s.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}
                    >
                      {usd(s.realized_pnl)}
                    </Td>
                    <Td align="right">{pct(s.avg_edge)}</Td>
                    <Td align="right">{usd(s.avg_pnl_per_trade)}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {/* Strategy A/B comparison */}
      <SectionCard title="Strategy A/B comparison">
        {Object.keys(data.ab_comparison.strategies).length === 0 ? (
          <EmptyState title="Not enough data for comparison" />
        ) : (
          <div className="space-y-4">
            <div className="text-xs text-neutral-500">
              Period: {new Date(data.ab_comparison.period.start).toLocaleDateString()} &ndash;{" "}
              {new Date(data.ab_comparison.period.end).toLocaleDateString()}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
                  <tr>
                    <Th>Strategy</Th>
                    <Th align="right">Trades</Th>
                    <Th align="right">Win rate</Th>
                    <Th align="right">Realized PnL</Th>
                    <Th align="right">Avg return</Th>
                    <Th align="right">Sharpe</Th>
                    <Th align="right">PF</Th>
                    <Th align="right">Max DD</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800">
                  {Object.entries(data.ab_comparison.strategies).map(([name, s]) => (
                    <tr key={name} className="hover:bg-neutral-900/50">
                      <Td className="font-medium text-neutral-100">{name}</Td>
                      <Td align="right">{s.trades}</Td>
                      <Td align="right">{pct(s.win_rate)}</Td>
                      <Td align="right" className={s.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}>
                        {usd(s.realized_pnl)}
                      </Td>
                      <Td align="right">{usd(s.avg_return_per_trade)}</Td>
                      <Td align="right">{num(s.sharpe)}</Td>
                      <Td align="right">{num(s.profit_factor)}</Td>
                      <Td align="right" className="text-rose-400">{pct(s.max_drawdown)}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </SectionCard>

      {/* Temporal patterns */}
      <SectionCard title="Time-of-day patterns">
        {data.temporal_patterns.by_hour.length === 0 ? (
          <EmptyState title="No temporal data yet" />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-wide text-neutral-500">By hour of day</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
                    <tr>
                      <Th>Hour</Th>
                      <Th align="right">Trades</Th>
                      <Th align="right">Win rate</Th>
                      <Th align="right">PnL</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800">
                    {data.temporal_patterns.by_hour.map((h) => (
                      <tr key={h.hour} className="hover:bg-neutral-900/50">
                        <Td>{h.hour.toString().padStart(2, "0")}:00</Td>
                        <Td align="right">{h.trades}</Td>
                        <Td align="right">{pct(h.win_rate)}</Td>
                        <Td
                          align="right"
                          className={h.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}
                        >
                          {usd(h.realized_pnl)}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-wide text-neutral-500">By day of week</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
                    <tr>
                      <Th>Day</Th>
                      <Th align="right">Trades</Th>
                      <Th align="right">Win rate</Th>
                      <Th align="right">PnL</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800">
                    {data.temporal_patterns.by_day_of_week.map((d) => (
                      <tr key={d.day} className="hover:bg-neutral-900/50">
                        <Td>{d.day}</Td>
                        <Td align="right">{d.trades}</Td>
                        <Td align="right">{pct(d.win_rate)}</Td>
                        <Td
                          align="right"
                          className={d.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}
                        >
                          {usd(d.realized_pnl)}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      {/* Market microstructure */}
      <SectionCard title="Market microstructure">
        {!data.microstructure.total_costs_paid && data.microstructure.total_costs_paid === 0 ? (
          <EmptyState title="No microstructure data yet" />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-wide text-neutral-500">Cost breakdown</div>
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="Total fees" value={usd(data.microstructure.total_fees_paid)} />
                <MetricCard label="Total slippage" value={usd(data.microstructure.total_slippage_paid)} />
                <MetricCard label="Total spread" value={data.microstructure.total_spread_paid.toFixed(4)} />
                <MetricCard
                  label="Costs / PnL"
                  value={`${data.microstructure.costs_as_pct_of_pnl.toFixed(1)}%`}
                  tone={data.microstructure.costs_as_pct_of_pnl > 20 ? "negative" : "neutral"}
                />
              </div>
            </div>
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-wide text-neutral-500">
                Adverse selection
              </div>
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="Adverse trades" value={String(data.microstructure.adverse_selection.adverse_trades)} />
                <MetricCard label="Favorable" value={String(data.microstructure.adverse_selection.favorable_trades)} />
                <MetricCard
                  label="Adverse rate"
                  value={pct(data.microstructure.adverse_selection.adverse_rate)}
                  tone={data.microstructure.adverse_selection.adverse_rate > 0.5 ? "negative" : "neutral"}
                />
                <MetricCard
                  label="Avg trade length"
                  value={`${data.microstructure.avg_trade_length_hours.toFixed(1)}h`}
                />
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      {/* Export */}
      <SectionCard title="Export">
        <div className="flex items-center gap-4">
          <p className="text-sm text-neutral-400">
            Download the full trade log as CSV for external analysis in Excel, Python, or R.
          </p>
          <a
            href={csvExportUrl}
            download
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
          >
            Export CSV
          </a>
        </div>
      </SectionCard>
    </div>
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
