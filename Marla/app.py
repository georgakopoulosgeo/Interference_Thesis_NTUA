from flask import Flask, request, Response
import requests
import itertools
from traffic_logger import increment_request_count, start_rps_logger_thread

# Configuration
SERVICE_TARGETS = [
    "http://192.168.49.2:30081",  # nginx-svc-node1 (NodePort)
    "http://192.168.49.3:30082",  # nginx-svc-node2 (NodePort)
]

# Round Robin target selection
target_cycle = itertools.cycle(SERVICE_TARGETS)

app = Flask(__name__)

start_rps_logger_thread() 

@app.route("/", methods=["GET", "POST"])
def handle_request():
    increment_request_count()  # Increment RPS counter
    target_url = next(target_cycle)

    try:
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
