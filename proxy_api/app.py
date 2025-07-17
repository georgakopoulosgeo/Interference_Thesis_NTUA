from flask import Flask, request, Response
import requests, itertools
from rps_logger import start_rps_logger_thread, RequestCounterMiddleware

# Round robin targets
SERVICE_TARGETS = [
    "http://192.168.49.2:30081",
    "http://192.168.49.3:30082",
]
target_cycle = itertools.cycle(SERVICE_TARGETS)

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = RequestCounterMiddleware(app.wsgi_app)
start_rps_logger_thread()

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
