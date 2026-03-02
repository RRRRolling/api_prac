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
    Monte Carlo simulation on simple returns.
    mu: daily mean return
    vol: daily volatility
    """
    daily_returns = np.random.normal(mu, vol, (simulations, days))
    price_paths = current_price * np.cumprod(1 + daily_returns, axis=1)

    final_prices = price_paths[:, -1]
    returns_sim = (final_prices - current_price) / current_price
    var_95 = np.percentile(returns_sim, 5)  # 5% left tail

    return {
        "paths": price_paths,
        # 展示为“潜在损失幅度(%)”
        "var_95": round(abs(var_95) * 100, 2)
    }

def get_risk_metrics(returns):
    if returns is None or len(returns) < 2:
        return {
            "vol": "N/A",
            "mdd": "N/A",
            "sharpe": "N/A",
            "mu": 0.0
        }

    vol = float(np.std(returns) * np.sqrt(252) * 100)

    rf = 0.02 / 252
    std = float(np.std(returns))
    sharpe = np.nan if std < 1e-12 else float((np.mean(returns) - rf) / std * np.sqrt(252))

    return {
        "vol": round(vol, 2),
        "sharpe": "N/A" if np.isnan(sharpe) else round(sharpe, 2),
        "mu": float(np.mean(returns))
    }

def flatten_columns_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    # yfinance 有时会给 MultiIndex columns，压平更稳
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df

def pick_price_col(df: pd.DataFrame) -> str:
    if "Close" in df.columns:
        return "Close"
    if "Adj Close" in df.columns:
        return "Adj Close"
    return ""

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
        ticker = ticker.upper().strip()

        # ===== Asset data =====
        df = yf.download(ticker, period="1y", auto_adjust=False, progress=False)
        if df is None or df.empty:
            return "Ticker not found."

        df = flatten_columns_if_needed(df)
        price_col = pick_price_col(df)
        if not price_col:
            return "Price column not found for asset."

        close = df[price_col].dropna()
        if close.empty:
            return "No valid price data for asset."

        returns = close.pct_change().dropna()
        if len(returns) < 2:
            return "Not enough asset data to analyze."

        current_price = float(close.iloc[-1])
        metrics = get_risk_metrics(returns)

        # ===== Benchmark: VOO =====
        bench_ticker = "VOO"
        df_bench = yf.download(bench_ticker, period="1y", auto_adjust=False, progress=False)
        if df_bench is None or df_bench.empty:
            return "Benchmark (VOO) data not available."

        df_bench = flatten_columns_if_needed(df_bench)
        bench_price_col = pick_price_col(df_bench)
        if not bench_price_col:
            return "Price column not found for benchmark."

        bench_close = df_bench[bench_price_col].dropna()
        bench_returns = bench_close.pct_change().dropna()

        # 对齐交易日
        aligned = pd.concat([returns.rename("asset"), bench_returns.rename("bench")], axis=1).dropna()
        asset_ret = aligned["asset"]
        bench_ret = aligned["bench"]

        # 累计收益（用于画“收益率曲线”）
        asset_cum = (1 + asset_ret).cumprod() - 1
        bench_cum = (1 + bench_ret).cumprod() - 1
        asset_total = float(asset_cum.iloc[-1] * 100)
        bench_total = float(bench_cum.iloc[-1] * 100)

        # 相对强弱（Ticker/VOO）
        rel_strength = (1 + asset_ret).cumprod() / (1 + bench_ret).cumprod()

        # beta / alpha（可选，但挺有用）
        cov = np.cov(asset_ret, bench_ret)[0, 1]
        var_b = np.var(bench_ret)
        beta = float(cov / var_b) if var_b > 1e-12 else np.nan
        alpha_daily = float(asset_ret.mean() - (0 if np.isnan(beta) else beta) * bench_ret.mean())
        alpha_ann = alpha_daily * 252 * 100

        # ===== Monte Carlo (5 trading days) =====
        daily_vol = (metrics["vol"] / 100) / np.sqrt(252) if metrics["vol"] != "N/A" else 0.0
        mc_res = run_monte_carlo(current_price, metrics["mu"], daily_vol, days=5, simulations=100)

        # ===== Plot 1: Cumulative Return (Ticker vs VOO) =====
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatter(x=asset_cum.index, y=asset_cum * 100, mode="lines", name=ticker))
        fig_cmp.add_trace(go.Scatter(x=bench_cum.index, y=bench_cum * 100, mode="lines", name="VOO"))
        fig_cmp.update_layout(
            title=f"{ticker} vs VOO: Cumulative Return (1Y)",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350
        )
        chart_cmp = plot(fig_cmp, output_type="div", include_plotlyjs=False)

        # ===== Plot 2: Relative Strength (Ticker/VOO) =====
        fig_rs = go.Figure()
        fig_rs.add_trace(go.Scatter(x=rel_strength.index, y=rel_strength, mode="lines", name=f"{ticker}/VOO"))
        fig_rs.update_layout(
            title=f"Relative Strength: {ticker} / VOO (1Y)",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300
        )
        chart_rs = plot(fig_rs, output_type="div", include_plotlyjs=False)

        # ===== Plot 3: Monte Carlo Paths =====
        fig_mc = go.Figure()
        for i in range(len(mc_res["paths"])):
            fig_mc.add_trace(go.Scatter(y=mc_res["paths"][i], mode="lines", line=dict(width=1), opacity=0.25, showlegend=False))
        fig_mc.update_layout(
            title=f"Monte Carlo: 100 Paths (Next 5 Trading Days)",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350
        )
        chart_mc = plot(fig_mc, output_type="div", include_plotlyjs=False)

        beta_show = "N/A" if np.isnan(beta) else f"{beta:.2f}"
        alpha_show = "N/A" if np.isnan(beta) else f"{alpha_ann:.2f}%"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: white; padding: 40px; }}
                .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #1e293b; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #334155; }}
                .stat-value {{ font-size: 22px; font-weight: bold; color: #60a5fa; margin-top: 10px; }}
                .chart-container {{ background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; }}
                .back-btn {{ color: #94a3b8; text-decoration: none; margin-bottom: 20px; display: inline-block; }}
                .highlight {{ color: #f87171; }}
                .subtle {{ color: #cbd5e1; font-size: 12px; margin-top: 6px; }}
            </style>
        </head>
        <body>
            <a href="/" class="back-btn">← Back to Terminal</a>
            <h1>{ticker} Risk Analysis Report</h1>

            <div class="grid">
                <div class="stat-card">
                    <div>Annualized Vol</div>
                    <div class="stat-value">{metrics['vol']}%</div>
                </div>
                <div class="stat-card">
                    <div>Sharpe Ratio</div>
                    <div class="stat-value">{metrics['sharpe']}</div>
                </div>
                <div class="stat-card">
                    <div>5D VaR (95%)</div>
                    <div class="stat-value highlight">{mc_res['var_95']}%</div>
                    <div class="subtle">Monte Carlo, 100 paths</div>
                </div>
                <div class="stat-card">
                    <div>1Y Return ({ticker})</div>
                    <div class="stat-value">{asset_total:.2f}%</div>
                    <div class="subtle">VOO: {bench_total:.2f}%</div>
                </div>
            </div>

            <div class="grid">
                <div class="stat-card">
                    <div>Beta vs VOO</div>
                    <div class="stat-value">{beta_show}</div>
                </div>
                <div class="stat-card">
                    <div>Alpha (ann., vs VOO)</div>
                    <div class="stat-value">{alpha_show}</div>
                </div>
                <div class="stat-card">
                    <div>Benchmark</div>
                    <div class="stat-value">VOO</div>
                </div>
                <div class="stat-card">
                    <div>Current Price</div>
                    <div class="stat-value">{current_price:.2f}</div>
                </div>
            </div>

            <div class="chart-container">{chart_cmp}</div>
            <div class="chart-container">{chart_rs}</div>
            <div class="chart-container">{chart_mc}</div>
        </body>
        </html>
        """

    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"