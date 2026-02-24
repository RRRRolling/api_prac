from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Quant API is Online"}

@app.get("/calculate_var")
def calculate_var(notional: float, sigma: float):
    var = 1.65 * sigma * notional
    return {"VaR_95": round(var, 2)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)