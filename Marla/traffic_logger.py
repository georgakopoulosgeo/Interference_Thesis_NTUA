import json
import os
from datetime import datetime
from threading import Lock

LOG_PATH = "logs/rps_schedule.jsonl"
_counter = 0
_lock = Lock()

import os
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def log_request():
    global _counter
    with _lock:
        _counter += 1

def flush_counter_to_log():
    global _counter
    timestamp = datetime.utcnow().isoformat()

    log_entry = {
        "timestamp": timestamp,
        "rps": _counter
    }

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"📝 Logged RPS: {_counter} @ {timestamp}")
    _counter = 0
