from flask import Flask, request, Response
import requests
import itertools
import time
import threading
import json
import os
from datetime import datetime

# Configuration
SERVICE_TARGETS = [
    "http://192.168.49.2:30081",
    "http://192.168.49.3:30082",
]

# Round Robin target selection
target_cycle = itertools.cycle(SERVICE_TARGETS)

app = Flask(__name__)

# Metrics variables
request_count = 0
metrics_lock = threading.Lock()
LOG_FILE = "logs/rps_schedule.json"

def ensure_log_dir():
    """Ensure logs directory exists"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def write_rps_log(rps):
    """Append RPS data to JSON log file"""
    ensure_log_dir()
    timestamp = datetime.now().isoformat()
    data = {timestamp: round(rps, 2)}  # Round to 2 decimal places
    
    try:
        # Read existing data if file exists
        existing = {}
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                existing = json.load(f)
        
        # Update with new data
        existing.update(data)
        
        # Write back to file
        with open(LOG_FILE, 'w') as f:
            json.dump(existing, f, indent=2)
            
    except Exception as e:
        print(f"Error writing RPS log: {e}")

def metrics_collector():
    """Collect and log RPS every 30 seconds"""
    global request_count
    while True:
        time.sleep(30)
        with metrics_lock:
            current_rps = request_count / 30  # Calculate RPS
            request_count = 0  # Reset counter
            write_rps_log(current_rps)
            print(f"Logged RPS: {current_rps:.2f}")

# Start metrics thread
metrics_thread = threading.Thread(target=metrics_collector, daemon=True)
metrics_thread.start()

@app.before_request
def count_request():
    """Increment request counter"""
    global request_count
    with metrics_lock:
        request_count += 1

@app.route("/", methods=["GET", "POST"])
def handle_request():
    target_url = next(target_cycle)

    try:
        if request.method == "GET":
            proxied = requests.get(target_url, headers=request.headers, timeout=5)
        elif request.method == "POST":
            proxied = requests.post(target_url, headers=request.headers, data=request.get_data(), timeout=5)
        else:
            return "Unsupported method", 405

        return Response(proxied.content, status=proxied.status_code, headers=dict(proxied.headers))

    except Exception as e:
        print(f"❌ Error forwarding to {target_url}: {e}")
        return "MARLA proxy error", 502

if __name__ == "__main__":
    ensure_log_dir()
    app.run(host="0.0.0.0", port=5000)