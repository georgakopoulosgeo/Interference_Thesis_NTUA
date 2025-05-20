from typing import Any, Dict, Iterable, Tuple
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

def csv_streamer(
    buffer_data: Iterable[Tuple[float, Dict[str, Any]]]
) -> Iterable[str]:
    """
    Generator that yields CSV lines for an iterable of (timestamp, metrics_dict).
    Preserves the original metrics order (as inserted into the dict).
    """
    # 1) Grab the first metrics dict to seed our column order
    it = iter(buffer_data)
    try:
        first_ts, first_metrics = next(it)
    except StopIteration:
        # no data → no CSV
        return
        yield  # make this a generator

    # Build the ordered list of metric keys, excluding 'timestamp' itself
    metric_keys = [k for k in first_metrics.keys() if k != "timestamp"]
    if "timestamp" in metric_keys:
        metric_keys.remove("timestamp")

    # 2) Any additional keys from later rows?
    for ts, metrics in it:
        for k in metrics.keys():
            if k != "timestamp" and k not in metric_keys:
                metric_keys.append(k)

    # Our header is always: timestamp + the metric keys
    header = metric_keys

    # 3) Write header
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    yield buf.getvalue()
    buf.seek(0); buf.truncate(0)

    # 4) Now stream every row *including* the first
    #    Re-iterate buffer_data from the top
    for ts, metrics in buffer_data:
        row = [ metrics.get(k, "") for k in metric_keys ]
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