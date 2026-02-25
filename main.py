from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yfinance as yf
import numpy as np
import pandas as pd

app = FastAPI()
# 使用 Jinja2 模板引擎
templates = Jinja2Templates(directory="templates") 
# 或者直接写在字符串里，但推荐存为 templates/index.html

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Duke Quant - Live Risk Engine</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f4f7f9; }
        .box { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        h2 { color: #001A57; text-align: center; }
        input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #001A57; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .res { margin-top: 25px; padding: 15px; background: #eef6ff; border-radius: 6px; border-left: 5px solid #001A57; }
        .error { color: #d9534f; background: #fdf7f7; border-left: 5px solid #d9534f; padding: 15px; margin-top: 20px; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>📈 Real-Time Stock Risk Analysis</h2>
        <form action="/analyze_stock" method="post">
            <p>Enter Stock Ticker (e.g., AAPL, NVDA, TSLA):</p>
            <input type="text" name="ticker" placeholder="AAPL" value="{{ ticker if ticker else '' }}" required>
            <button type="submit">Get Risk Metrics</button>
        </form>

        {% if error %}
        <div class="error">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endif %}

        {% if vol %}
        <div class="res">
            <h3>{{ ticker }} Risk Assessment (1-Year)</h3>
            <p><b>Annualized Volatility:</b> {{ vol }}%</p>
            <p><b>Maximum Drawdown:</b> {{ mdd }}%</p>
            <p><small>* Data Source: Yahoo Finance</small></p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# 为了演示方便，直接手动创建 Template 对象
from starlette.templating import _TemplateResponse

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # 使用 jinja2 渲染，不会出现 {{ }} 占位符
    return HTMLResponse(content=render_template(request))

@app.post("/analyze_stock", response_class=HTMLResponse)
async def analyze(request: Request, ticker: str = Form(...)):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty or len(df) < 5:
            return HTMLResponse(content=render_template(request, error=f"No data found for {ticker}"))

        # 计算收益率并移除空值
        returns = df['Close'].pct_change().dropna()
        
        # 1. 年化波动率
        vol = returns.std() * np.sqrt(252) * 100
        
        # 2. 最大回撤 (MDD)
        cum_rets = (1 + returns).cumprod()
        running_max = cum_rets.cummax()
        drawdown = (cum_rets - running_max) / running_max
        max_dd = drawdown.min() * 100

        return HTMLResponse(content=render_template(request, 
                                                  ticker=ticker.upper(), 
                                                  vol=round(vol, 2), 
                                                  mdd=round(max_dd, 2)))
    except Exception as e:
        return HTMLResponse(content=render_template(request, error=str(e)))

def render_template(request, **context):
    from jinja2 import Template
    return Template(HTML_TEMPLATE).render(request=request, **context)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)