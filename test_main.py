import pytest
from fastapi.testclient import TestClient
from main import app

# 创建测试客户端
client = TestClient(app)

def test_index_page():
    """测试主页加载"""
    response = client.get("/")
    assert response.status_code == 200
    assert "FastAPI Risk Calculator" in response.text

def test_var_calculation():
    """测试 VaR 接口逻辑"""
    # 模拟参数访问
    response = client.get("/calculate_var?notional=1000&sigma=0.02")
    assert response.status_code == 200
    assert response.json() == {"VaR_95": 33.0}

def test_risk_calc_post():
    """测试表单提交后的计算逻辑"""
    # FastAPI 处理 Form 数据的方式与 Flask 略有不同
    response = client.post("/", data={"returns_data": "0.01, -0.02, 0.05"})
    assert response.status_code == 200
    assert "Volatility" in response.text
    assert "Max Drawdown" in response.text
    