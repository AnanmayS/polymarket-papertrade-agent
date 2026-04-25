"""Probability and trading math helpers."""

from __future__ import annotations

import math


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value into a closed interval."""

    return max(minimum, min(maximum, value))


def midpoint_probability(best_bid: float, best_ask: float, last_trade_price: float) -> float:
    """Estimate implied probability from market pricing."""

    if best_bid > 0 and best_ask > 0:
        return clamp((best_bid + best_ask) / 2.0, 0.01, 0.99)
    return clamp(last_trade_price, 0.01, 0.99)


def edge_from_probabilities(fair_probability: float, market_probability: float) -> float:
    """Simple edge estimate used throughout the app."""

    return fair_probability - market_probability


def expected_value_proxy(fair_probability: float, fill_price: float) -> float:
    """Expected value proxy for a binary share priced in [0, 1]."""

    return (fair_probability * (1 - fill_price)) - ((1 - fair_probability) * fill_price)


def kelly_fraction(fair_probability: float, market_price: float) -> float:
    """Fractional Kelly sizing for a binary contract."""

    market_price = clamp(market_price, 0.01, 0.99)
    fair_probability = clamp(fair_probability, 0.01, 0.99)
    b = (1 - market_price) / market_price
    q = 1 - fair_probability
    raw_fraction = ((b * fair_probability) - q) / max(b, 1e-9)
    return clamp(raw_fraction, 0.0, 1.0)


def sharpe_like(returns: list[float]) -> float:
    """Lightweight Sharpe-style metric for irregular paper trades."""

    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    if math.isclose(variance, 0.0):
        return 0.0
    return mean / math.sqrt(variance)


def max_drawdown(series: list[float]) -> float:
    """Compute max drawdown over an equity curve."""

    if not series:
        return 0.0
    peak = series[0]
    max_dd = 0.0
    for value in series:
        peak = max(peak, value)
        drawdown = (peak - value) / peak if peak else 0.0
        max_dd = max(max_dd, drawdown)
    return max_dd
