import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main  # 你的 main.py

client = TestClient(main.app)


def _make_price_df(seed=0, n=260, start="2025-01-01", init_price=100.0):
    """
    生成稳定的模拟价格数据（Close列），避免测试随机失败。
    n=260 大约一年交易日
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start=start, periods=n)  # business days

    # 生成温和波动的收益率
    rets = rng.normal(loc=0.0004, scale=0.01, size=n)
    prices = init_price * np.cumprod(1 + rets)
    df = pd.DataFrame({"Close": prices}, index=idx)
    return df


@pytest.fixture
def mock_yf_download(monkeypatch):
    """
    mock yfinance.download：
    - 用户ticker返回一份价格表
    - VOO返回另一份价格表
    """

    def _fake_download(ticker, period="1y", auto_adjust=False, progress=False):
        ticker = (ticker or "").upper()
        if ticker == "VOO":
            return _make_price_df(seed=42, init_price=400.0)
        # 其他ticker都返回 asset 数据
        return _make_price_df(seed=7, init_price=120.0)

    monkeypatch.setattr(main.yf, "download", _fake_download)


def test_home_page_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert "Quant Risk Terminal" in r.text
    assert "<form" in r.text


def test_analyze_ok_with_mocked_data(mock_yf_download):
    r = client.post("/analyze", data={"ticker": "NVDA"})
    assert r.status_code == 200

    # 页面关键内容检查
    assert "NVDA Risk Analysis Report" in r.text
    assert "VOO" in r.text  # benchmark 出现
    assert "Cumulative Return" in r.text  # 收益率曲线标题
    assert "Monte Carlo" in r.text  # MC 图标题
    assert "5D VaR" in r.text  # VaR 卡片


def test_analyze_handles_empty_df(monkeypatch):
    # 让 yfinance.download 返回空表 => 应该提示 Ticker not found.
    def _empty_download(*args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(main.yf, "download", _empty_download)

    r = client.post("/analyze", data={"ticker": "XXXX"})
    assert r.status_code == 200
    assert "Ticker not found" in r.text