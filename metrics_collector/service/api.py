from fastapi import FastAPI, HTTPException, Response
import csv
import io
from collector.sampler import Sampler

app = FastAPI(title="Metrics Collector API")

# Start sampling immediately
sampler = Sampler(interval_sec=20.0, buffer_window_sec=40.0)
sampler.start()

@app.get("/metrics")
def get_metrics(window: int = 20):
    """
    Return the last `window` seconds of PCM metrics (system‐domain only) as CSV.
    """
    try:
        data = sampler.buffer.snapshot(window)
        if not data:
            return Response(content="", media_type="text/csv")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)

        return Response(content=output.getvalue(), media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
