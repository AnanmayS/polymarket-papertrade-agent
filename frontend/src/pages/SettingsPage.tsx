import { useApi } from "../hooks/useApi";
import { api } from "../api/client";
import { SectionCard } from "../components/SectionCard";
import { EmptyState } from "../components/EmptyState";
import { LoadingBlock } from "../components/LoadingBlock";

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const usd = (value: number) =>
  value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

const LABELS: Record<string, { label: string; format: (value: number) => string }> = {
  initial_bankroll: { label: "Initial bankroll", format: usd },
  min_liquidity: { label: "Min liquidity", format: usd },
  min_volume: { label: "Min volume", format: usd },
  max_spread: { label: "Max spread", format: (value) => value.toFixed(3) },
  min_confidence: { label: "Min confidence", format: pct },
  max_position_size_pct: { label: "Max position size", format: pct },
  max_market_exposure_pct: { label: "Max market exposure", format: pct },
  max_category_exposure_pct: { label: "Max category exposure", format: pct },
  max_daily_loss_pct: { label: "Max daily loss", format: pct },
  max_open_trades: { label: "Max open trades", format: (value) => value.toFixed(0) },
  fractional_kelly: { label: "Fractional Kelly", format: (value) => value.toFixed(2) },
};

export function SettingsPage() {
  const { data, loading, error } = useApi(() => api.settings(), []);

  return (
    <SectionCard title="Risk rules">
      {loading ? (
        <LoadingBlock />
      ) : error ? (
        <EmptyState title="Couldn't load rules" hint={error} />
      ) : !data ? (
        <EmptyState title="No rules" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-neutral-800">
              {Object.entries(data).map(([key, value]) => {
                const meta = LABELS[key];
                const display =
                  typeof value === "number" && meta ? meta.format(value) : String(value);

                return (
                  <tr key={key}>
                    <td className="px-3 py-2 text-neutral-400">{meta?.label || key}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-neutral-100">
                      {display}
                    </td>
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
