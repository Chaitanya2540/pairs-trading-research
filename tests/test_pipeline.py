"""
Regression tests for the pairs-trading pipeline.

These tests pin the current canonical numbers for HDFC/ICICI on both regimes.
If you make a change to signals/backtest/metrics that legitimately moves these
numbers, update the assertions and explain in the commit message what changed
and why. The point of pinning these is to *force* that conversation.
"""

import pytest

from pairs.pipeline import run_pipeline, PipelineParams


# ── Stable regime (Apr 2024 – Jan 2026) ──────────────────────────────────────
# Headline numbers reported in README, results/final_results.md, and the
# resume bullet. Refit only if the strategy has changed intentionally.

class TestStableRegimeHDFC_ICICI:
    @pytest.fixture(scope="class")
    def result(self):
        return run_pipeline("HDFC_ICICI", PipelineParams(end="2026-01-30"))

    def test_trade_count(self, result):
        assert result["summary"]["n_trades"] == 6

    def test_win_rate(self, result):
        assert result["summary"]["win_rate_pct"] == pytest.approx(83.33, abs=0.05)

    def test_sharpe(self, result):
        # Sharpe rounded to 2dp is the resume number — keep the tolerance
        # tight so a real regression breaks the build.
        assert result["summary"]["sharpe"] == pytest.approx(1.00, abs=0.02)

    def test_max_drawdown_pct(self, result):
        assert result["summary"]["max_drawdown_pct"] == pytest.approx(-52.0, abs=0.5)

    def test_profit_factor(self, result):
        assert result["summary"]["profit_factor"] == pytest.approx(5.53, abs=0.1)

    def test_total_pnl(self, result):
        assert result["summary"]["total_pnl"] == pytest.approx(93.47, abs=0.5)


# ── Full dataset (Apr 2024 – Mar 2026) ───────────────────────────────────────

class TestFullDatasetHDFC_ICICI:
    @pytest.fixture(scope="class")
    def result(self):
        return run_pipeline("HDFC_ICICI", PipelineParams())

    def test_trade_count(self, result):
        assert result["summary"]["n_trades"] == 7

    def test_win_rate(self, result):
        assert result["summary"]["win_rate_pct"] == pytest.approx(71.43, abs=0.05)

    def test_sharpe(self, result):
        assert result["summary"]["sharpe"] == pytest.approx(0.57, abs=0.02)

    def test_regime_delta(self, result):
        # The whole project's narrative depends on the stable regime
        # outperforming the full sample. If this assertion ever fails, the
        # central story has broken.
        full_sharpe = result["summary"]["sharpe"]
        stable = run_pipeline("HDFC_ICICI", PipelineParams(end="2026-01-30"))
        stable_sharpe = stable["summary"]["sharpe"]
        assert stable_sharpe > full_sharpe + 0.3, (
            f"Expected stable regime Sharpe to beat full by ≥0.3 — "
            f"got stable={stable_sharpe:.3f}, full={full_sharpe:.3f}"
        )


# ── Sanity: the pipeline produces consistent shapes ──────────────────────────

class TestPipelineShape:
    def test_returns_required_keys(self):
        r = run_pipeline("HDFC_ICICI", PipelineParams(end="2026-01-30"))
        for key in ("pair", "leg1", "leg2", "params", "hedge", "spread",
                    "zscore", "daily", "trades", "summary"):
            assert key in r, f"missing key {key!r}"

    def test_daily_has_expected_columns(self):
        r = run_pipeline("HDFC_ICICI", PipelineParams(end="2026-01-30"))
        for col in ("spread", "zscore", "position", "mtm_pnl", "trade_pnl",
                    "daily_pnl", "cum_pnl"):
            assert col in r["daily"].columns, f"missing daily column {col!r}"

    def test_unknown_pair_raises(self):
        with pytest.raises(KeyError, match="Unknown pair"):
            run_pipeline("DOES_NOT_EXIST")
