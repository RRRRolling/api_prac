from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot

app = FastAPI()

def run_monte_carlo(current_price, mu, vol, days=5, simulations=100):
    """
    进行蒙特卡洛模拟
    mu: 日均收益率
    vol: 日波动率
    """
    # 模拟 100 条路径，每条走 5 天
    # 几何布朗运动公式简版：S_t = S_0 * exp(sum(r))
    daily_returns = np.random.normal(mu, vol, (simulations, days))
    # 计算价格路径 (simulations x days)
    price_paths = current_price * np.cumprod(1 + daily_returns, axis=1)
    
    # 计算预测的 1-Week VaR (95% 置信度下的潜在亏损)
    final_prices = price_paths[:, -1]
    returns_sim = (final_prices - current_price) / current_price
    var_95 = np.percentile(returns_sim, 5)
    
    return {
        "paths": price_paths,
        "var_95": round(abs(var_95) * 100, 2)
    }

def get_risk_metrics(returns, benchmark_returns=None):
    if len(returns) < 2:
        return {k: "N/A" for k in ["vol", "mdd", "sharpe", "mu"]}
    
    vol = np.std(returns) * np.sqrt(252) * 100
    cum_rets = (1 + returns).cumprod()
    running_max = np.maximum.accumulate(cum_rets)
    drawdown = (cum_rets - running_max) / running_max
    max_dd = np.min(drawdown) * 100
    
    rf = 0.02 / 252
    sharpe = (np.mean(returns) - rf) / np.std(returns) * np.sqrt(252)
    
    return {
        "vol": round(vol, 2),
        "mdd": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "mu": np.mean(returns), # 用于蒙特卡洛
        "drawdown_series": drawdown
    }

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Duke Quant Terminal</title>
        <style>
            body { font-family: 'Inter', sans-serif; margin: 0; background: #0f172a; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .card { background: #1e293b; border-radius: 12px; padding: 30px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); text-align: center; }
            input { background: #334155; border: 1px solid #475569; color: white; padding: 12px; border-radius: 6px; width: 250px; font-size: 16px; }
            button { background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-left: 10px; }
            h2 { margin-bottom: 20px; color: #60a5fa; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 Quant Risk Terminal</h2>
            <form action="/analyze" method="post">
                <input type="text" name="ticker" placeholder="Enter Ticker (e.g. NVDA)" required>
                <button type="submit">Run Full Analysis</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(ticker: str = Form(...)):
    try:
        ticker = ticker.upper()
        df = yf.download(ticker, period="1y")
        if df.empty: return "Ticker not found."
        
        price_col = 'Close' if 'Close' in df.columns else 'Adj Close'
        df['Returns'] = df[price_col].pct_change()
        clean_returns = df['Returns'].dropna()
        
        # 1. 基础指标计算
        metrics = get_risk_metrics(clean_returns)
        current_price = float(df[price_col].iloc[-1])
        
        # 2. 蒙特卡洛模拟 (5天预测)
        # 使用日波动率 (vol/100/sqrt(252))
        daily_vol = (metrics['vol'] / 100) / np.sqrt(252)
        mc_res = run_monte_carlo(current_price, metrics['mu'], daily_vol)
        
        # 3. 生成回撤图 (Plotly)
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=clean_returns.index, y=metrics['drawdown_series'] * 100, fill='tozeroy', line=dict(color='#ef4444'), name="Drawdown"))
        fig_dd.update_layout(title=f"{ticker} Max Drawdown (1Y History)", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350)
        chart_dd = plot(fig_dd, output_type='div', include_plotlyjs=False)

        # 4. 生成蒙特卡洛路径图 (Plotly)
        fig_mc = go.Figure()
        for i in range(len(mc_res['paths'])):
            fig_mc.add_trace(go.Scatter(y=mc_res['paths'][i], mode='lines', line=dict(width=1), opacity=0.3, showlegend=False))
        fig_mc.update_layout(title=f"Monte Carlo: 100 Paths (Next 5 Days)", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350)
        chart_mc = plot(fig_mc, output_type='div', include_plotlyjs=False)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: white; padding: 40px; }}
                .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #1e293b; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #334155; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #60a5fa; margin-top: 10px; }}
                .chart-container {{ background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; }}
                .back-btn {{ color: #94a3b8; text-decoration: none; margin-bottom: 20px; display: inline-block; }}
                .highlight {{ color: #f87171; }}
            </style>
        </head>
        <body>
            <a href="/" class="back-btn">← Back to Terminal</a>
            <h1>{ticker} Risk Analysis Report</h1>
            
            <div class="grid">
                <div class="stat-card"><div>Annualized Vol</div><div class="stat-value">{metrics['vol']}%</div></div>
                <div class="stat-card"><div>Max Drawdown</div><div class="stat-value">{metrics['mdd']}%</div></div>
                <div class="stat-card"><div>Sharpe Ratio</div><div class="stat-value">{metrics['sharpe']}</div></div>
                <div class="stat-card"><div>1-Week VaR (95%)</div><div class="stat-value highlight">{mc_res['var_95']}%</div></div>
            </div>

            <div class="chart-container">{chart_dd}</div>
            <div class="chart-container">{chart_mc}</div>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error: {str(e)}"