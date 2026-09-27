"""Backtest exposes a complete research archive, including no-trade results."""

from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from tests.conftest import make_ohlcv


def test_backtest_can_render_research_archive_download():
    frame = make_ohlcv(360, trend="volatile")
    app = AppTest.from_file("app.py").run(timeout=20)
    app.radio[0].set_value("Backtest").run(timeout=20)
    with patch("ui.page_backtest.fetch_ohlcv", return_value=frame), patch("ui.page_backtest.render_price_chart"):
        app.button(key="backtest_run").click().run(timeout=20)
    assert not app.exception
    assert not app.error
    downloads = app.get("download_button")
    assert any(button.proto.label == "Download research archive" for button in downloads)
