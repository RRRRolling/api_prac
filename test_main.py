import pytest
from main import app

@pytest.fixture
def client():
    # 创建一个测试客户端，模拟浏览器行为
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_page(client):
    """测试主页是否能正常加载"""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b"Quant Risk Calc" in rv.data

def test_var_calculation(client):
    """测试你写的 VaR 计算接口"""
    # 模拟访问 /calculate_var?notional=1000&sigma=0.02
    rv = client.get('/calculate_var?notional=1000&sigma=0.02')
    json_data = rv.get_json()
    
    assert rv.status_code == 200
    # 1.65 * 0.02 * 1000 = 33.0
    assert json_data['VaR_95'] == 33.0

def test_risk_calc_post(client):
    """测试网页表单提交计算回撤的逻辑"""
    # 模拟用户在网页上输入收益率序列
    test_data = {'returns': '0.01, -0.02, 0.05'}
    rv = client.post('/', data=test_data)
    
    assert rv.status_code == 200
    assert b"Volatility" in rv.data  # 确认结果页面包含波动率字样
    