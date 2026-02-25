from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import numpy as np

app = FastAPI(title="Quant Risk Engine")

# HTML 模板 - 包含计算器界面
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Quant Risk Calc</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background-color: #f4f7f6; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }
        h2 { color: #001A57; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; }
        button { padding: 10px 20px; background: #001A57; color: white; border: none; cursor: pointer; }
        .result { margin-top: 20px; padding: 15px; background: #e7f3ff; border-left: 4px solid #001A57; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 FastAPI Risk Calculator</h2>
        <form method="POST">
            <p>输入收益率序列 (逗号分隔):</p>
            <input type="text" name="returns_data" placeholder="0.01, -0.02, 0.05" required>
            <button type="submit">计算风险指标</button>
        </form>
        {% if volatility %}
        <div class="result">
            <p><b>Volatility:</b> {{ volatility }}%</p>
            <p><b>Max Drawdown:</b> {{ max_drawdown }}%</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    # 初始页面加载，手动替换模板占位符（由于未配置独立模板文件夹）
    return HTML_TEMPLATE.replace("{% if volatility %}", "").replace("{% endif %}", "")

@app.post("/", response_class=HTMLResponse)
async def calculate_ui(returns_data: str = Form(...)):
    try:
        rets = np.array([float(x.strip()) for x in returns_data.split(',')])
        vol = round(np.std(rets) * np.sqrt(252) * 100, 2)
        
        cum_rets = np.cumprod(1 + rets)
        running_max = np.maximum.accumulate(cum_rets)
        max_dd = round(np.min((cum_rets - running_max) / running_max) * 100, 2)
        
        # 渲染结果
        res_html = HTML_TEMPLATE.replace("{% if volatility %}", "").replace("{% endif %}", "")
        res_html = res_html.replace("{{ volatility }}", str(vol)).replace("{{ max_drawdown }}", str(max_dd))
        return res_html
    except:
        return "Input Error: Please use comma-separated numbers."

@app.get("/calculate_var")
async def calculate_var(notional: float, sigma: float):
    # 保持你原始的业务逻辑
    var = 1.65 * sigma * notional
    return {"VaR_95": round(var, 2)}