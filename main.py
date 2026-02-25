from fastapi import FastAPI
from flask import Flask, request, render_template_string
import numpy as np
import uvicorn

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Duke Quant Risk Calc</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f7f6; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }
        h2 { color: #001A57; border-bottom: 2px solid #001A57; padding-bottom: 10px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #001A57; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0033a0; }
        .result { margin-top: 20px; padding: 15px; background: #e7f3ff; border-left: 5px solid #001A57; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 云端量化风险计算器 (Main 引擎)</h2>
        <p>请输入日收益率序列（逗号隔开）:</p>
        <form method="POST">
            <input type="text" name="returns" placeholder="例如: 0.01, -0.005, 0.02, -0.01" required>
            <button type="submit">运行风险评估</button>
        </form>

        {% if result %}
        <div class="result">
            <p><b>年化波动率:</b> {{ result.volatility }}%</p>
            <p><b>最大回撤:</b> {{ result.max_drawdown }}%</p>
            <p><small>* 基于 252 个交易日假设</small></p>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''
@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        try:
            raw_data = request.form.get('returns')
            # 这里的解析逻辑非常适合处理金融时间序列数据
            returns = [float(x.strip()) for x in raw_data.split(',')]
            
            # 计算波动率
            vol = np.std(returns) * np.sqrt(252) * 100
            
            # 计算最大回撤 (Risk Engineering 核心指标)
            cum_rets = np.cumprod(1 + np.array(returns))
            running_max = np.maximum.accumulate(cum_rets)
            drawdown = (cum_rets - running_max) / running_max
            max_dd = np.min(drawdown) * 100

            result = {"volatility": round(vol, 2), "max_drawdown": round(max_dd, 2)}
        except Exception as e:
            result = {"volatility": "Error", "max_drawdown": "解析失败，请检查数据格式"}
            
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == "__main__":
    # 本地调试时使用 8000 端口
    app.run(host='0.0.0.0', port=8000)