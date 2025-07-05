from fastapi import FastAPI
from fastapi.responses import JSONResponse
import joblib
import os

app = FastAPI()
model = None
model_path = os.path.join("models", "slowdown_predictor.pkl")

@app.on_event("startup")
def load_model():
    global model
    try:
        model = joblib.load(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        raise RuntimeError("Model loading failed.")

@app.get("/healthz")
def health_check():
    if model is not None:
        return JSONResponse(content={"status": "ok", "message": "Model loaded."}, status_code=200)
    else:
        return JSONResponse(content={"status": "error", "message": "Model not loaded."}, status_code=500)
