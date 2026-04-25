export type Market = {
  id: number;
  slug: string;
  question: string;
  category: string;
  subcategory: string | null;
  sports_league: string | null;
  event_title: string | null;
  active: boolean;
  closed: boolean;
  liquidity: number;
  volume: number;
  best_bid: number;
  best_ask: number;
  last_trade_price: number;
  spread: number;
  implied_probability: number;
  opportunity_score: number;
  resolution_time: string | null;
  metadata_json: Record<string, unknown>;
};

export type Signal = {
  id: number;
  market_id: number;
  market_question: string;
  event_title: string;
  mode: string;
  status: string;
  market_probability: number;
  fair_probability: number;
  edge: number;
  expected_value_proxy: number;
  confidence: number;
  opportunity_score: number;
  rationale: string;
  features: Record<string, number>;
  feature_importance: Record<string, number>;
  risk: {
    approved: boolean;
    reason_codes: string[];
    proposed_stake: number;
  } | null;
  created_at: string;
};

export type Position = {
  id: number;
  market_id: number;
  side: string;
  status: string;
  quantity: number;
  avg_price: number;
  cost_basis: number;
  market_price: number;
  realized_pnl: number;
  unrealized_pnl: number;
};

export type Trade = {
  id: number;
  market_id: number;
  market_question: string;
  market_url?: string | null;
  side: string;
  status: string;
  stake: number;
  quantity: number;
  fill_price: number;
  exit_price: number;
  fees_paid: number;
  slippage_paid: number;
  realized_pnl: number;
  unrealized_pnl: number;
  confidence: number;
  entry_edge: number;
  rationale: string;
  opened_at: string | null;
  settled_at: string | null;
};

export type EquityPoint = {
  timestamp: string;
  bankroll: number;
  realized_pnl: number;
  unrealized_pnl: number;
};

export type MarketPerformance = {
  market_id: number;
  label: string;
  realized_pnl: number;
  trades: number;
  win_rate: number;
};

export type Portfolio = {
  bankroll: number;
  cash: number;
  realized_pnl: number;
  unrealized_pnl: number;
  current_equity: number;
  open_exposure: number;
  win_rate: number;
  average_edge: number;
  sharpe_like: number;
  max_drawdown: number;
  open_positions: Position[];
  equity_curve: EquityPoint[];
  per_market: MarketPerformance[];
};

export type Postmortem = {
  id: number;
  trade_id: number;
  market_id: number;
  market_question: string;
  final_result: string;
  pnl: number;
  sizing_assessment: string;
  lessons_learned: string;
  summary: string;
  feature_drivers_json: Record<string, number>;
  created_at: string;
};

export type RiskSettings = {
  initial_bankroll: number;
  min_liquidity: number;
  min_volume: number;
  max_spread: number;
  min_confidence: number;
  max_position_size_pct: number;
  max_market_exposure_pct: number;
  max_category_exposure_pct: number;
  max_daily_loss_pct: number;
  max_open_trades: number;
  fractional_kelly: number;
  default_signal_mode: string;
};
