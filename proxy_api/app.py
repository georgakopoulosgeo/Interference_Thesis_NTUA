from flask import Flask, request, Response
import requests, itertools, threading, time, json, os
from datetime import datetime

# Constants
LOG_PATH = "/home/george/logs/rps.json"
LOG_INTERVAL = 30  # seconds

# Round robin targets
SERVICE_TARGETS = [
    "http://192.168.49.2:30081",
    "http://192.168.49.3:30082",
]
target_cycle = itertools.cycle(SERVICE_TARGETS)
SESSIONS = {target: requests.Session() for target in SERVICE_TARGETS}

# Initialize Flask app
app = Flask(__name__)

# Request counter (thread-safe)
request_count = 0
lock = threading.Lock()

def log_rps():
    global request_count
    while True:
        time.sleep(LOG_INTERVAL)
        with lock:
            count = request_count
            request_count = 0
        rps = count / LOG_INTERVAL
        entry = {"timestamp": datetime.now().isoformat(), "rps": rps}
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"Logged RPS: {entry}")

# Start the logger thread when the app module is loaded
def start_logger_thread():
    t = threading.Thread(target=log_rps, daemon=True)
    t.start()

start_logger_thread()

@app.route("/", methods=["GET", "POST"])
def handle_request():
    global request_count
    with lock:
        request_count += 1

    target_url = next(target_cycle)
    session = SESSIONS[target_url]

    try:
        if request.method == "GET":
            proxied = session.get(target_url, headers=request.headers, timeout=5)
        elif request.method == "POST":
            proxied = session.post(target_url, headers=request.headers, data=request.get_data(), timeout=5)
        else:
            return "Unsupported method", 405

        return Response(proxied.content, status=proxied.status_code, headers=dict(proxied.headers))

    except Exception as e:
        print(f"❌ Error forwarding to {target_url}: {e}")
        return "MARLA proxy error", 502
