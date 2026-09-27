"""Forecast targets, cost policy and bounded probability interpretation."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from backtesting.engine import run_backtest
from indicators.forecast import TimesFMForecast
from ml.timesfm_runtime import TimesFMRuntime, TimesFMForecast as Forecast, probability_above
from signals.base import SignalDirection
from tests.test_backtest_accounting import bars


class FixedQuantileModel:
    def __init__(self, terminal_quantiles):
        self.values = np.asarray(terminal_quantiles)
        self.calls = 0

    def forecast(self, horizon, inputs):
        self.calls += 1
        point = np.full((len(inputs), horizon), self.values[4])
        output = np.empty((len(inputs), horizon, 10))
        output[:, :, 0] = point
        output[:, :, 1:] = self.values
        return point, output


def indicator(values):
    model = FixedQuantileModel(values)
    return TimesFMForecast(TimesFMRuntime(model_factory=lambda: model)), model


def test_tail_estimates_never_extrapolate_to_certainty():
    forecast = Forecast(1, np.array([100.]),
                        {i / 10: np.array([90. + 2.5 * (i - 1)]) for i in range(1, 10)}, "test", "test")
    assert probability_above(forecast, 89) == pytest.approx(0.9)
    assert probability_above(forecast, 111) == pytest.approx(0.1)
    assert probability_above(forecast, 100) == pytest.approx(0.5)


@pytest.mark.parametrize("horizon", [1, 5, 10])
def test_backtest_uses_historical_origins_and_matching_target_even_with_interactive_runtime(horizon):
    forecast, model = indicator(np.linspace(101, 109, 9))
    df = bars(120)
    with patch.object(forecast.runtime, "forecast", wraps=forecast.runtime.forecast) as inference:
        report = run_backtest(df, {forecast.name: forecast}, "TEST", "1y", horizon_days=horizon)
    assert inference.call_count == 1  # the adapter may split this into multiple chunks
    assert report.trades
    for trade in report.trades:
        origin = df.index.get_loc(trade.signal_date)
        assert (origin - 31) % horizon == 0
        assert trade.exit_date == trade.target_date == df.index[origin + horizon]
    assert forecast.runtime.config.use_case == "interactive"


@pytest.mark.parametrize("values", [np.linspace(99, 103, 9), np.linspace(97, 101, 9)])
def test_configured_cost_changes_trade_eligibility_on_both_sides(values):
    forecast, _ = indicator(values)
    df = bars(120)
    low = run_backtest(df, {forecast.name: forecast}, "TEST", "1y", cost_per_trade_pct=0)
    high = run_backtest(df, {forecast.name: forecast}, "TEST", "1y", cost_per_trade_pct=5)
    assert low.trades
    assert not high.trades


def test_short_requires_probability_of_clearing_costs_not_just_any_decline():
    forecast, _ = indicator([99.7, 99.75, 99.8, 99.85, 99.89, 99.99, 100.01, 100.02, 100.03])
    computed = forecast.compute_for_backtest(bars(122), 5, 0.1)
    assert forecast.latest_analysis.probability_down > 0.6
    assert forecast.latest_analysis.probability_short_profit < 0.6
    assert forecast.get_signal_for_horizon(computed, 5).direction == SignalDirection.HOLD


def test_profit_hurdles_match_two_fill_accounting():
    forecast, _ = indicator(np.linspace(95, 105, 9))
    forecast.compute_for_backtest(bars(122), 5, 2)
    analysis = forecast.latest_analysis
    assert analysis.cost_per_trade_pct == 2
    assert analysis.probability_profit == probability_above(analysis.forecast, 100 * 1.01 / 0.99)
    assert analysis.probability_short_profit == 1 - probability_above(analysis.forecast, 100 * 0.99 / 1.01)


@pytest.mark.parametrize("length", [117, 120, 122])
def test_historical_forecast_availability_does_not_depend_on_future_bars(length):
    forecast, _ = indicator(np.linspace(101, 109, 9))
    df = bars(125)
    full = forecast.compute_for_backtest(df, 5, 0.1)
    prefix = forecast.compute_for_backtest(df.iloc[:length], 5, 0.1)
    columns = [name for name in full if name.startswith("TFM_")]
    pd.testing.assert_frame_equal(full[columns].iloc[:length], prefix[columns])


def test_failed_historical_forecast_is_not_retried_for_every_bar():
    forecast, model = indicator(np.linspace(101, 109, 9))
    def fail(horizon, inputs):
        model.calls += 1
        raise RuntimeError("Unavailable model")
    model.forecast = fail
    report = run_backtest(bars(120), {forecast.name: forecast}, "TEST", "1y")
    assert not report.trades
    assert model.calls == 1
