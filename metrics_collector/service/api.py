from fastapi import FastAPI, HTTPException, Response
import csv
import io
from collector.sampler import Sampler

app = FastAPI(title="Metrics Collector API")

# Configure for:
# - 20s collection duration
# - 60s between samples
# - 60s buffer retention
sampler = Sampler(collection_duration_sec=20.0, sampling_interval_sec=60.0,buffer_window_sec=60.0)
sampler.start()  # Start the background thread

@app.get("/metrics")
def get_metrics(window: int = 20):
    """Returns metrics with PCM's native timestamps in CSV format."""
    try:
        data_points = sampler.buffer.snapshot(window)
        if not data_points:
            return Response("No data available", media_type="text/plain")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data_points[0].keys())
        writer.writeheader()
        writer.writerows(data_points)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment;filename=pcm_metrics.csv"}
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/debug/buffer")
def debug_buffer():
    """Inspect raw buffer contents (for debugging)."""
    with sampler.buffer.lock:  # Ensure thread-safe access
        buffer_data = list(sampler.buffer.buffer)  # Get all (timestamp, metrics) pairs
    
    return {
        "buffer_size": len(buffer_data),
        "window_sec": sampler.buffer.window_size,
        "samples": buffer_data,
    }