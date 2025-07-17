import threading
import time
import json
import os
from datetime import datetime
import redis

# Redis client
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
REDIS_KEY = "proxy_request_count"

# Log file path
from config import LOG_PATH
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def increment_request_count():
    try:
        r.incr(REDIS_KEY)
    except Exception as e:
        print(f"⚠️ Redis increment failed: {e}")

def log_rps_loop(interval=30):
    while True:
        time.sleep(interval)

        try:
            count = int(r.getset(REDIS_KEY, 0) or 0)
            rps = round(count / interval, 2)

            entry = {"timestamp": datetime.now().isoformat(), "rps": rps}

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
            print(f"❌ Error logging RPS: {e}")

def start_rps_logger_thread():
    t = threading.Thread(target=log_rps_loop, daemon=True)
    t.start()

class RequestCounterMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        increment_request_count()
        return self.app(environ, start_response)
