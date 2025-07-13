import csv
import threading
import time
import io
import csv

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

def metrics_to_csv(metrics: list[dict]) -> str:
    """
    Converts list of dicts (metrics) into CSV-formatted string.
    """
    if not metrics:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=metrics[0].keys())
    writer.writeheader()
    writer.writerows(metrics)
    return output.getvalue()

def parse_csv_rows(rows: list[list[str]]) -> list[dict]:
    """
    Filters and parses rows from PCM based on core-domain and desired keywords.
    Returns list of dicts for API response.
    """
    if len(rows) < 3:
        #print("[pcm_reader] CSV file has fewer than 3 rows — skipping.")
        return []

    header_domain = rows[0]
    header_metric = rows[1]
    data_rows = rows[2:]

    #print(f"[pcm_reader] Header domain columns: {len(header_domain)}")
    #print(f"[pcm_reader] Header metric columns: {len(header_metric)}")

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
    
    #print(f"[pcm_reader] Keeping {len(indices_to_keep)} columns: {final_headers[:5]}...")

    # Parse selected data rows into dicts
    result = []
    for i,row in enumerate(data_rows):
        if len(row) < max(indices_to_keep) + 1:
            #print(f"[pcm_reader] Skipping row {i} with only {len(row)} columns.")
            continue
        filtered = [row[i] for i in indices_to_keep]
        result.append(dict(zip(final_headers, filtered)))
    #print(f"[pcm_reader] Parsed {len(result)} metrics from CSV.")
    return result

def metrics_to_csv(metrics: list[dict]) -> str:
    """
    Converts list of dicts (metrics) into CSV-formatted string.
    """
    if not metrics:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=metrics[0].keys())
    writer.writeheader()
    writer.writerows(metrics)
    return output.getvalue()


def periodic_buffer_refresh(buffer_path: str, cache: dict, interval: int = 5):
    """Periodically refreshes shared_cache with latest metrics."""
    while True:
        try:
            raw_rows = read_buffer_csv(buffer_path)
            print(f"[pcm_reader] Read {len(raw_rows)} rows from buffer.")
            parsed = parse_csv_rows(raw_rows)
            print(f"[pcm_reader] Parsed {len(parsed)} metrics.")
            cache["metrics"] = parsed
        except Exception as e:
            print(f"[pcm_reader] Error reading buffer: {e}")
            cache["metrics"] = []
        time.sleep(interval)


def init_metrics_updater(buffer_path: str) -> dict:
    """Initializes background thread and returns shared cache reference."""
    thread = threading.Thread(target=periodic_buffer_refresh, args=(buffer_path, shared_cache), daemon=True)
    thread.start()
    return shared_cache
