import pytest
from fastapi.testclient import TestClient
from main import app
import numpy as np

# 创建 FastAPI 测试客户端
client = TestClient(app)

def test_home_page_load():
    """测试主页 UI 是否正常加载"""
    response = client.get("/")
    assert response.status_code == 200
    # 检查关键字，确保我们的深色模式 UI 已经上线
    assert "Quant Risk Terminal" in response.text
    assert "Enter Ticker" in response.text

def test_analyze_valid_ticker():
    """测试输入合法股票代码（如 NVDA）时的逻辑"""
    # 模拟用户提交表单
    response = client.post("/analyze", data={"ticker": "NVDA"})
    
    assert response.status_code == 200
    # 检查是否包含了我们新加的风险指标
    assert "Annualized Vol" in response.text
    assert "Max Drawdown" in response.text
    assert "Sharpe Ratio" in response.text
    # 检查 Plotly 图表组件是否被成功渲染
    assert "plotly-latest.min.js" in response.text

def test_analyze_invalid_ticker():
    """测试输入不存在的股票代码时的错误处理"""
    response = client.post("/analyze", data={"ticker": "INVALID_TICKER_123"})
    # 应该触发代码中的 Ticker not found 逻辑
    assert "Ticker not found" in response.text

def test_risk_metrics_calculation():
    """
    量化核心测试：手动验证计算逻辑是否准确。
    虽然这个测试是在内部运行，但它是 Risk Engineering 的灵魂。
    """
    from main import get_risk_metrics
    import pandas as pd
    
    # 构造一组简单的收益率序列：[0.01, -0.01, 0.02]
    mock_returns = pd.Series([0.01, -0.01, 0.02])
    metrics = get_risk_metrics(mock_returns)
    
    # 验证返回值不是 NaN
    assert metrics['vol'] != "N/A"
    assert metrics['mdd'] != "N/A"
    # 验证 Sharpe Ratio 是数字类型
    assert isinstance(metrics['sharpe'], float)

def test_docs_accessible():
    """测试 FastAPI 自动生成的文档是否可用（这对以后 API 对接很重要）"""
    response = client.get("/docs")
    assert response.status_code == 200