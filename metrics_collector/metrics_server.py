from fastapi import FastAPI
import pandas as pd
import subprocess
import os
from threading import Thread
from pathlib import Path

app = FastAPI()
PCM_CSV = Path("/var/pcm/metrics.csv")
SAMPLE_RATE = 2  # seconds

def pcm_collector():
    cores = os.getenv("ASSIGNED_CORES", "0-2")
    cmd = f"pcm -r -csv={PCM_CSV} -cores={cores}"
    subprocess.run(cmd.split(), check=True)

@app.on_event("startup")
def start_pcm():
    Path("/var/pcm").mkdir(exist_ok=True)
    Thread(target=pcm_collector, daemon=True).start()

@app.get("/metrics")
def get_metrics():
    try:
        df = pd.read_csv(PCM_CSV)
        return {
            "node": os.getenv("NODE_NAME"),
            "cores": os.getenv("ASSIGNED_CORES"),
            "metrics": df.tail(10).to_dict(orient="records")
        }
    except Exception as e:
        return {"error": str(e)}