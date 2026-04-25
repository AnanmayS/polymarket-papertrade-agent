import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { api, isApiConfigured } from "../api/client";
import { EngineControls } from "../components/EngineControls";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/markets", label: "Markets" },
  { to: "/ideas", label: "Trade Ideas" },
  { to: "/trades", label: "Paper Trades" },
  { to: "/reviews", label: "Reviews" },
  { to: "/rules", label: "Rules" },
];

function fmtUsd(value: number | undefined | null) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function fmtPct(value: number | undefined | null) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function AppShell() {
  const location = useLocation();
  const configured = isApiConfigured();
  const { data: portfolio, refetch } = useApi(
    () => (configured ? api.portfolio() : Promise.resolve(null)),
    [configured],
  );

  const equity = portfolio?.current_equity;
  const realized = portfolio?.realized_pnl;
  const winRate = portfolio?.win_rate;

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-200">
      <header className="sticky top-0 z-20 border-b border-neutral-800 bg-neutral-950/80 backdrop-blur">
        <div className="flex items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-sm font-semibold tracking-tight text-neutral-100">
              Polymarket Paper Agent
            </span>
          </div>

          <div className="hidden items-center gap-6 md:flex">
            <Stat label="Equity" value={fmtUsd(equity)} />
            <Stat
              label="Realized PnL"
              value={fmtUsd(realized)}
              tone={(realized ?? 0) >= 0 ? "pos" : "neg"}
            />
            <Stat label="Win rate" value={fmtPct(winRate)} />
          </div>

          <EngineControls onRan={refetch} />
        </div>
      </header>

      <div className="flex">
        <aside className="hidden w-52 shrink-0 border-r border-neutral-800 md:block">
          <nav className="sticky top-[57px] flex flex-col gap-0.5 p-3">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm transition ${
                    isActive
                      ? "bg-neutral-800 text-neutral-100"
                      : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <nav className="fixed bottom-0 left-0 right-0 z-20 flex justify-around border-t border-neutral-800 bg-neutral-950/95 px-2 py-2 backdrop-blur md:hidden">
          {NAV.map((item) => {
            const active =
              item.to === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={`rounded px-2 py-1 text-[11px] ${
                  active ? "text-emerald-400" : "text-neutral-500"
                }`}
              >
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <main className="min-w-0 flex-1 px-4 pb-24 pt-6 sm:px-6 md:pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg";
}) {
  const color =
    tone === "pos"
      ? "text-emerald-400"
      : tone === "neg"
        ? "text-rose-400"
        : "text-neutral-100";

  return (
    <div className="flex flex-col leading-tight">
      <span className="text-[10px] uppercase tracking-wide text-neutral-500">{label}</span>
      <span className={`text-sm font-semibold tabular-nums ${color}`}>{value}</span>
    </div>
  );
}
