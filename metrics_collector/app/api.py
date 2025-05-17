from fastapi import FastAPI, HTTPException
from .collector import CollectorService
import logging

app = FastAPI()
collector = CollectorService()

@app.on_event("startup")
async def startup():
    collector.start()
    logging.info("Metrics collector started")

@app.on_event("shutdown")
async def shutdown():
    collector.stop()
    logging.info("Metrics collector stopped")

@app.get("/metrics")
async def get_metrics(window_seconds: int = 20):
    if window_seconds > 30 or window_seconds < 1:
        raise HTTPException(
            status_code=400,
            detail="Window size must be between 1-30 seconds"
        )
    
    metrics = collector.get_metrics(window_seconds)
    if "error" in metrics:
        raise HTTPException(
            status_code=503,
            detail=metrics["error"]
        )
    
    return metrics

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "last_sample_time": collector.buffer.last_sample_time
    }