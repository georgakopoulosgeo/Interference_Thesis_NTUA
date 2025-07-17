import threading
import time
import json
import os

# Shared request counter
request_counter = {
    "count": 0
}
lock = threading.Lock()

LOG_PATH = "/home/logs/rps.json"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def log_rps_loop(interval=30):
    while True:
        time.sleep(interval)
        with lock:
            count = request_counter["count"]
            request_counter["count"] = 0

        rps = count / interval
        entry = {
            "timestamp": int(time.time()),
            "rps": round(rps, 2)
        }

        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r+") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = []
                    data.append(entry)
                    f.seek(0)
                    json.dump(data, f, indent=2)
            else:
                with open(LOG_PATH, "w") as f:
                    json.dump([entry], f, indent=2)
        except Exception as e:
            print(f"⚠️ Error writing RPS log: {e}")

def start_rps_logger_thread():
    t = threading.Thread(target=log_rps_loop, daemon=True)
    t.start()

def increment_request_count():
    with lock:
        request_counter["count"] += 1
