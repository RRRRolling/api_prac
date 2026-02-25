import pytest
from fastapi.testclient import TestClient
from main import app
import numpy as np

client = TestClient(app)

def test_home_page():
    """验证主页 UI 加载"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Quant Risk Terminal" in response.text

def test_monte_carlo_logic():
    """
    量化核心测试：验证蒙特卡洛模拟函数
    确保它能生成正确的路径维度，并且 VaR 是合理的数字
    """
    from main import run_monte_carlo
    
    current_price = 100.0
    mu = 0.001
    vol = 0.02
    days = 5
    sims = 50
    
    result = run_monte_carlo(current_price, mu, vol, days=days, simulations=sims)
    
    # 验证路径形状: (50条路径, 5天)
    assert result['paths'].shape == (sims, days)
    # 验证 VaR 是正数（百分比绝对值）
    assert result['var_95'] >= 0
    # 验证 VaR 不应是 N/A 或 NaN
    assert not np.isnan(result['var_95'])

def test_analyze_endpoint_structure():
    """
    集成测试：验证分析页面结构
    检查是否包含新增加的指标卡片和图表容器
    """
    # 使用 NVDA 作为测试用例，如果网络不通则不强制报错（容错处理）
    response = client.post("/analyze", data={"ticker": "NVDA"})
    
    assert response.status_code == 200
    
    # 如果抓取成功，验证新 UI 元素
    if "Risk Analysis Report" in response.text:
        assert "1-Week VaR (95%)" in response.text
        assert "Monte Carlo: 100 Paths" in response.text
        assert "plotly-latest.min.js" in response.text
    else:
        # 如果由于网络原因失败，确保显示的是预期的错误信息
        assert "Error" in response.text or "not found" in response.text

def test_fastapi_docs():
    """确保文档页面可用，方便面试展示"""
    response = client.get("/docs")
    assert response.status_code == 200