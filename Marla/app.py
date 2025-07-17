from flask import Flask, request, Response
import requests
import itertools
import time
import threading

from traffic_logger import log_request, flush_counter_to_log


# Configuration
SERVICE_TARGETS = [
    "http://192.168.49.2:30081",  # nginx-svc-node1 (NodePort)
    "http://192.168.49.3:30082",  # nginx-svc-node2 (NodePort)
]

# Round Robin target selection
target_cycle = itertools.cycle(SERVICE_TARGETS)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def handle_request():
    target_url = next(target_cycle)

    try:
        # Log the request RPS (used in ARIMA)
        log_request()

        # Forward the request (Only GET/POST for now)
        if request.method == "GET":
            proxied = requests.get(target_url, headers=request.headers, timeout=5)
        elif request.method == "POST":
            proxied = requests.post(target_url, headers=request.headers, data=request.get_data(), timeout=5)
        else:
            return "Unsupported method", 405

        #print(f"→ Forwarded to: {target_url} | Status: {proxied.status_code}")
        return Response(proxied.content, status=proxied.status_code, headers=dict(proxied.headers))

    except Exception as e:
        print(f"❌ Error forwarding to {target_url}: {e}")
        return "MARLA proxy error", 502

def background_flusher():
    while True:
        time.sleep(60)
        flush_counter_to_log()

if __name__ == "__main__":
    threading.Thread(target=background_flusher, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
