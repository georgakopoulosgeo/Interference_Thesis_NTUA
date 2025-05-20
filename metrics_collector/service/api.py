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

import io
import csv
from typing import Iterable, Tuple, Dict, Any

def csv_streamer(
    buffer_data: Iterable[Tuple[float, Dict[str, Any]]]
) -> Iterable[str]:
    """
    Takes an iterable of (timestamp, metrics_dict) and yields CSV lines.
    First row is the header: timestamp,date,time,<metric1>,<metric2>,...
    """
    # 1) Gather all possible metric keys
    all_keys = set()
    for _, metrics in buffer_data:
        all_keys.update(metrics.keys())
    # 2) Define the ordered columns: drop any duplicates of timestamp/date/time
    metric_keys = sorted(k for k in all_keys if k not in ("timestamp", "date", "time"))
    header = ["timestamp", "date", "time"] + metric_keys

    # 3) Create a CSV writer on a StringIO buffer
    buf = io.StringIO()
    writer = csv.writer(buf)
    # Emit header
    writer.writerow(header)
    yield buf.getvalue()
    buf.seek(0); buf.truncate(0)

    # 4) Emit each row
    for ts, metrics in buffer_data:
        row = [
            # timestamp from the tuple
            f"{ts:.6f}",
            # raw date/time strings (or blank if missing)
            metrics.get("date", ""),
            metrics.get("time", ""),
        ]
        # then each metric in our sorted list
        for key in metric_keys:
            val = metrics.get(key, "")
            row.append("" if val is None else str(val))
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