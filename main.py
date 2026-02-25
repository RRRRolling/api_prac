from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
import yfinance as yf
import numpy as np
import pandas as pd

app = FastAPI()

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
    </style>
</head>
<body>
    <div class="box">
        <h2>📈 Real-Time Stock Risk Analysis</h2>
        <form action="/analyze_stock" method="post">
            <p>Enter Stock Ticker (e.g.: AAPL, NVDA, TSLA):</p>
            <input type="text" name="ticker" placeholder="AAPL" required>
            <button type="submit">Get Risk Metrics</button>
        </form>
        {% if ticker %}
        <div class="res">
            <h3>{{ ticker }} Risk Assessment (1-year)</h3>
            <p><b>Annualized Volatility:</b> {{ vol }}%</p>
            <p><b>Maximum Drawdown:</b> {{ mdd }}%</p>
            <p><small>* Data Source: Yahoo Finance</small></p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_TEMPLATE.replace("{% if ticker %}", "").replace("{% endif %}", "")

@app.post("/analyze_stock", response_class=HTMLResponse)
async def analyze(ticker: str = Form(...)):
    try:
        # 1. 抓取数据 (过去 1 年)
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty:
            raise ValueError("未找到数据")

        # 2. 计算日收益率
        df['Returns'] = df['Close'].pct_change().dropna()
        clean_returns = df['Returns'].dropna().values
        
        # 3. 风险计算
        if len(clean_returns) < 2:
            vol = 0.0
            max_dd = 0.0
        else:
            vol = np.std(clean_returns) * np.sqrt(252) * 100
        
            cum_rets = (1 + df['Returns']).cumprod()
            running_max = cum_rets.cummax()
            drawdown = (cum_rets - running_max) / running_max
            max_dd = drawdown.min() * 100

        # 4. 渲染结果
        res_html = HTML_TEMPLATE.replace("{% if ticker %}", "").replace("{% endif %}", "")
        res_html = res_html.replace("{{ ticker }}", ticker.upper())
        res_html = res_html.replace("{{ vol }}", str(round(vol, 2)))
        res_html = res_html.replace("{{ mdd }}", str(round(max_dd, 2)))
        return res_html
    except Exception as e:
        return f"<h3>分析失败: {ticker}</h3><p>错误原因: {str(e)}</p><a href='/'>返回</a>"