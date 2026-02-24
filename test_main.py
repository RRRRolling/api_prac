from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_var_calculation():
    # 测试 1000 本金，1% 波动率, 发送请求
    response = client.get("/calculate_var?notional=10000&sigma=0.01")
    assert response.status_code == 200
    assert response.json()["VaR_95"] == 165.0
    
    