from fastapi.testclient import TestClient
from main import app # 确保你的主程序文件名是 main.py

client = TestClient(app)

def test_home_load():
    response = client.get("/")
    assert response.status_code == 200
    # 核心：匹配你 HTML 里的英文标题
    assert "Real-Time Stock Risk Analysis" in response.text

def test_analyze_logic():
    # 测试提交一个真实存在的代码
    response = client.post("/analyze_stock", data={"ticker": "AAPL"})
    assert response.status_code == 200
    # 检查返回结果中是否包含大写的 AAPL
    assert "AAPL" in response.text.upper()
    # 检查是否算出了波动率数值（通常包含百分号）
    assert "Volatility" in response.text

def test_invalid_ticker():
    # 增加一个容错测试：输入不存在的股票代码
    response = client.post("/analyze_stock", data={"ticker": "NON_EXISTENT_TICKER"})
    assert response.status_code == 200
    # 检查是否显示了你代码中定义的错误提示
    assert "分析失败" in response.text or "Error" in response.text