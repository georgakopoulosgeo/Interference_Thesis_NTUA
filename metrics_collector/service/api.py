from fastapi import FastAPI, HTTPException, Response
import csv
import io
from collector.sampler import Sampler
from fastapi.responses import StreamingResponse

app = FastAPI(title="Metrics Collector API")

# Configure for:
# - 20s collection duration
# - 60s between samples
# - 60s buffer retention
sampler = Sampler(collection_duration_sec=20.0, sampling_interval_sec=60.0,buffer_window_sec=60.0)
sampler.start()  # Start the background thread

def csv_streamer(buffer_data):
    """
    Generator that yields CSV lines (as strings) for a list of
    (timestamp, metrics_dict) tuples.
    """
    # 1) Build header row from union of all metric keys
    metric_keys = set()
    for ts, metrics in buffer_data:
        metric_keys.update(metrics.keys())
    headers = ['timestamp'] + sorted(metric_keys)

    # 2) Write header
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    yield buf.getvalue()
    buf.seek(0); buf.truncate(0)

    # 3) Write each data row
    for ts, metrics in buffer_data:
        row = [ts] + [metrics.get(k, '') for k in headers if k != 'timestamp']
        writer.writerow(row)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)


@app.get("/metrics")
def get_metrics():
    # snapshot under lock
    with sampler.buffer.lock:
        buffer_data = list(sampler.buffer.buffer)

    # return a streaming CSV response
    return StreamingResponse(
        csv_streamer(buffer_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=metrics.csv"
        }
    )

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