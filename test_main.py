from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_home_load():
    response = client.get("/")
    assert response.status_code == 200
    assert "股票风险实时分析" in response.text

def test_analyze_logic():
    # 测试提交一个真实存在的代码
    response = client.post("/analyze_stock", data={"ticker": "AAPL"})
    assert response.status_code == 200
    assert "AAPL" in response.text
    