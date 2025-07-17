from flask import Flask, request, Response
import requests, threading, time, json

SERVICE_TARGETS = [
    "http://192.168.49.2:30081",
    "http://192.168.49.3:30082",
]

app = Flask(__name__)

target_lock = threading.Lock()
target_index = 0

thread_local = threading.local()

def get_next_target():
    global target_index
    with target_lock:
        target = SERVICE_TARGETS[target_index]
        target_index = (target_index + 1) % len(SERVICE_TARGETS)
        return target

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

@app.route("/", methods=["GET", "POST"])
def handle_request():
    target_url = get_next_target()
    session = get_session()

    try:
        headers = {k: v for k, v in request.headers if k.lower() != 'host'}

        if request.method == "GET":
            proxied = session.get(target_url, headers=headers, timeout=5)
        elif request.method == "POST":
            proxied = session.post(target_url, headers=headers, data=request.get_data(), timeout=5)
        else:
            return "Unsupported method", 405

        return Response(proxied.content, status=proxied.status_code, headers=dict(proxied.headers))

    except Exception as e:
        print(f"❌ Error forwarding to {target_url}: {e}")
        return "MARLA proxy error", 502
