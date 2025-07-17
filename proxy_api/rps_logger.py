import time, json, os
from datetime import datetime
import redis

LOG_PATH = "/home/george/logs/rps.json"
INTERVAL = 30

REDIS = redis.Redis(host='localhost', port=6379, decode_responses=True)

while True:
    time.sleep(INTERVAL)
    count = int(REDIS.get("proxy:rps_counter") or 0)
    REDIS.set("proxy:rps_counter", 0)
    rps = count / INTERVAL
    entry = {"timestamp": datetime.now().isoformat(), "rps": rps}
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Logged RPS: {entry}")
