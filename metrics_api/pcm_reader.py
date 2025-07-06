import csv
import threading
import time

BUFFER_PATH = "/opt/pcm_metrics/buffer_metrics.csv"
DESIRED_KEYWORDS = [
    "ipc", "l2miss", "l3miss", "read", "write", "c0res%", "c1res%", "c6res%"
]
DOMAIN_FILTER = "core"

shared_cache = {"metrics": []}


def read_buffer_csv(buffer_path: str) -> list[list[str]]:
    """Reads raw rows from buffer CSV (including headers)."""
    with open(buffer_path, mode='r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows


def parse_csv_rows(rows: list[list[str]]) -> list[dict]:
    """
    Filters and parses rows from PCM based on core-domain and desired keywords.
    Returns list of dicts for API response.
    """
    if len(rows) < 3:
        return []

    header_domain = rows[0]
    header_metric = rows[1]
    data_rows = rows[2:]

    # Build final headers and indices to keep
    indices_to_keep = []
    final_headers = []
    for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
        met_lower = met.strip().lower()
        dom_lower = dom.strip().lower()
        if met_lower in ("date", "time"):
            indices_to_keep.append(idx)
            final_headers.append(f"{met}")
        elif any(kw in met_lower for kw in DESIRED_KEYWORDS) and DOMAIN_FILTER in dom_lower:
            indices_to_keep.append(idx)
            final_headers.append(f"{dom.strip()} - {met.strip()}")

    # Parse selected data rows into dicts
    result = []
    for row in data_rows:
        filtered = [row[i] for i in indices_to_keep]
        result.append(dict(zip(final_headers, filtered)))
    return result


def periodic_buffer_refresh(buffer_path: str, cache: dict, interval: int = 2):
    """Periodically refreshes shared_cache with latest metrics."""
    while True:
        try:
            raw_rows = read_buffer_csv(buffer_path)
            parsed = parse_csv_rows(raw_rows)
            cache["metrics"] = parsed
        except Exception as e:
            print(f"[pcm_reader] Error reading buffer: {e}")
            cache["metrics"] = []
        time.sleep(interval)


def init_metrics_updater(buffer_path: str) -> dict:
    """Initializes background thread and returns shared cache reference."""
    thread = threading.Thread(
        target=periodic_buffer_refresh, args=(buffer_path, shared_cache), daemon=True
    )
    thread.start()
    return shared_cache
