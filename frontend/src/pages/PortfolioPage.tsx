import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useApi } from "../hooks/useApi";
import { api } from "../api/client";
import { MetricCard } from "../components/MetricCard";
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

export function PortfolioPage() {
  const { data, loading, error } = useApi(() => api.portfolio(), []);

  if (loading) return <LoadingBlock />;
  if (error) return <EmptyState title="Couldn't load portfolio" hint={error} />;
  if (!data) return <EmptyState title="No portfolio data" />;

  const realizedTone = data.realized_pnl >= 0 ? "positive" : "negative";
  const unrealizedTone = data.unrealized_pnl >= 0 ? "positive" : "negative";

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Equity" value={usd(data.current_equity)} />
        <MetricCard label="Cash" value={usd(data.cash)} />
        <MetricCard
          label="Realized PnL"
          value={usd(data.realized_pnl)}
          tone={realizedTone}
        />
        <MetricCard
          label="Unrealized"
          value={usd(data.unrealized_pnl)}
          tone={unrealizedTone}
        />
        <MetricCard label="Exposure" value={usd(data.open_exposure)} />
        <MetricCard
          label="Win rate"
          value={pct(data.win_rate)}
          sub={`Avg edge ${pct(data.average_edge)}`}
        />
      </div>

      <SectionCard title="Equity curve">
        {data.equity_curve.length === 0 ? (
          <EmptyState title="No equity history yet" hint="Run the agent to start building history." />
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <LineChart data={data.equity_curve}>
                <CartesianGrid stroke="#262626" strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  stroke="#525252"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value) =>
                    new Date(value).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  }
                />
                <YAxis
                  stroke="#525252"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value) => `$${Math.round(value)}`}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0a0a0a",
                    border: "1px solid #262626",
                    borderRadius: 6,
                  }}
                  labelFormatter={(value) => new Date(value as string).toLocaleString()}
                  formatter={(value: number) => usd(value)}
                />
                <Line
                  type="monotone"
                  dataKey="bankroll"
                  stroke="#34d399"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Open positions">
        {data.open_positions.length === 0 ? (
          <EmptyState title="No open positions" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <Th>Market</Th>
                  <Th>Side</Th>
                  <Th>Status</Th>
                  <Th align="right">Qty</Th>
                  <Th align="right">Avg</Th>
                  <Th align="right">Mark</Th>
                  <Th align="right">PnL</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {data.open_positions.map((position) => {
                  const pnl = position.realized_pnl + position.unrealized_pnl;
                  const sideLabel =
                    position.side === "buy_yes"
                      ? "yes"
                      : position.side === "buy_no"
                        ? "no"
                        : position.side;
                  const sideTone =
                    sideLabel === "yes"
                      ? "positive"
                      : sideLabel === "no"
                        ? "info"
                        : "neutral";

                  return (
                    <tr key={position.id} className="hover:bg-neutral-900/50">
                      <Td>#{position.market_id}</Td>
                      <Td>
                        <StatusPill tone={sideTone}>{sideLabel}</StatusPill>
                      </Td>
                      <Td>
                        <StatusPill>{position.status}</StatusPill>
                      </Td>
                      <Td align="right">{position.quantity.toFixed(2)}</Td>
                      <Td align="right">{position.avg_price.toFixed(3)}</Td>
                      <Td align="right">{position.market_price.toFixed(3)}</Td>
                      <Td
                        align="right"
                        className={pnl >= 0 ? "text-emerald-400" : "text-rose-400"}
                      >
                        {usd(pnl)}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Results by market">
        {data.per_market.length === 0 ? (
          <EmptyState title="No closed trades yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <Th>Market</Th>
                  <Th align="right">Trades</Th>
                  <Th align="right">Win rate</Th>
                  <Th align="right">Realized PnL</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {data.per_market.map((market) => (
                  <tr key={market.market_id} className="hover:bg-neutral-900/50">
                    <Td className="max-w-md truncate">{market.label}</Td>
                    <Td align="right">{market.trades}</Td>
                    <Td align="right">{pct(market.win_rate)}</Td>
                    <Td
                      align="right"
                      className={
                        market.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                      }
                    >
                      {usd(market.realized_pnl)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
