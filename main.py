from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot

app = FastAPI()

def get_risk_metrics(returns, benchmark_returns=None):
    """计算核心风险指标"""
    if len(returns) < 2:
        return {k: "N/A" for k in ["vol", "mdd", "sharpe", "beta"]}
    
    # 1. 年化波动率
    vol = np.std(returns) * np.sqrt(252) * 100
    
    # 2. 最大回撤
    cum_rets = (1 + returns).cumprod()
    running_max = np.maximum.accumulate(cum_rets)
    drawdown = (cum_rets - running_max) / running_max
    max_dd = np.min(drawdown) * 100
    
    # 3. 夏普比率 (假设无风险利率 2%)
    rf = 0.02 / 252
    sharpe = (np.mean(returns) - rf) / np.std(returns) * np.sqrt(252)
    
    return {
        "vol": round(vol, 2),
        "mdd": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "drawdown_series": drawdown
    }

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Duke Quant Terminal</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: 'Inter', sans-serif; margin: 0; background: #0f172a; color: white; }
            .container { max-width: 1000px; margin: 50px auto; padding: 20px; }
            .card { background: #1e293b; border-radius: 12px; padding: 25px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
            input { background: #334155; border: 1px solid #475569; color: white; padding: 12px; border-radius: 6px; width: 250px; }
            button { background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 600; }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px; }
            .stat-card { background: #334155; padding: 15px; border-radius: 8px; text-align: center; }
            .stat-value { font-size: 24px; font-weight: bold; color: #60a5fa; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h2>🚀 Quant Risk Terminal</h2>
                <form action="/analyze" method="post">
                    <input type="text" name="ticker" placeholder="Enter Ticker (e.g. NVDA)" required>
                    <button type="submit">Run Full Analysis</button>
                </form>
            </div>
            <div id="results"></div>
        </div>
    </body>
    </html>
    """

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(ticker: str = Form(...)):
    try:
        # 1. 获取数据
        ticker = ticker.upper()
        df = yf.download(ticker, period="1y")
        if df.empty: return "Ticker not found."
        
        # 2. 数据清洗与收益率计算
        
        price_col = 'Close' if 'Close' in df.columns else 'Adj Close'
        
        if price_col not in df.columns:
            return f"Error: Required price columns not found. Available: {list(df.columns)}"

        df['Returns'] = df[price_col].pct_change()
        clean_returns = df['Returns'].dropna()
        
        # 3. 计算指标
        metrics = get_risk_metrics(clean_returns)
        
        # 4. 生成 Plotly 水下回撤图
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=clean_returns.index, 
            y=metrics['drawdown_series'] * 100,
            fill='tozeroy',
            line=dict(color='#ef4444'),
            name="Drawdown"
        ))
        fig.update_layout(
            title=f"{ticker} Maximum Drawdown Analysis",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_title="Drawdown (%)",
            height=400
        )
        chart_html = plot(fig, output_type='div', include_plotlyjs=False)

        # 5. 组合最终页面
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: white; padding: 40px; }}
                .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #1e293b; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #334155; }}
                .stat-value {{ font-size: 28px; font-weight: bold; color: #3b82f6; }}
                .back-btn {{ color: #94a3b8; text-decoration: none; display: inline-block; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <a href="/" class="back-btn">← Back to Terminal</a>
            <h1>{ticker} Analysis Report</h1>
            <div class="grid">
                <div class="stat-card"><div>Annualized Vol</div><div class="stat-value">{metrics['vol']}%</div></div>
                <div class="stat-card"><div>Max Drawdown</div><div class="stat-value">{metrics['mdd']}%</div></div>
                <div class="stat-card"><div>Sharpe Ratio</div><div class="stat-value">{metrics['sharpe']}</div></div>
            </div>
            <div style="background: #1e293b; padding: 20px; border-radius: 12px;">
                {chart_html}
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error: {str(e)}"