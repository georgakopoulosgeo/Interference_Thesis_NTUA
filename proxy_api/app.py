from fastapi import FastAPI, Request, Response
import httpx
import threading

app = FastAPI()

# Target backend services
SERVICE_TARGETS = [
    "http://192.168.49.2:30081",
    "http://192.168.49.3:30082",
]

target_lock = threading.Lock()
target_index = 0

# Thread-local client session for httpx
thread_local = threading.local()

def get_next_target():
    global target_index
    with target_lock:
        target = SERVICE_TARGETS[target_index]
        target_index = (target_index + 1) % len(SERVICE_TARGETS)
        return target

def get_client():
    if not hasattr(thread_local, "client"):
        thread_local.client = httpx.AsyncClient()
    return thread_local.client

@app.api_route("/", methods=["GET", "POST"])
async def handle_proxy(request: Request):
    target_url = get_next_target()
    client = get_client()

    try:
        headers = {k.decode(): v.decode() for k, v in request.headers.raw if k.decode().lower() != "host"}
        body = await request.body()

        if request.method == "GET":
            proxied = await client.get(target_url, headers=headers, timeout=5.0)
        elif request.method == "POST":
            proxied = await client.post(target_url, content=body, headers=headers, timeout=5.0)
        else:
            return Response("Unsupported method", status_code=405)

        return Response(content=proxied.content, status_code=proxied.status_code, headers=proxied.headers)

    except Exception as e:
        print(f"❌ Error forwarding to {target_url}: {e}")
        return Response("MARLA proxy error", status_code=502)
