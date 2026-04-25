import pytest

from app.utils.math import edge_from_probabilities, expected_value_proxy, midpoint_probability


def test_midpoint_probability_prefers_bid_ask_mid() -> None:
    probability = midpoint_probability(0.42, 0.48, 0.99)
    assert probability == pytest.approx(0.45)


def test_midpoint_probability_falls_back_to_last_trade() -> None:
    probability = midpoint_probability(0.0, 0.0, 0.37)
    assert probability == pytest.approx(0.37)


def test_edge_calculation() -> None:
    assert edge_from_probabilities(0.61, 0.55) == pytest.approx(0.06)


def test_expected_value_proxy() -> None:
    value = expected_value_proxy(0.6, 0.52)
    assert round(value, 4) == 0.08
