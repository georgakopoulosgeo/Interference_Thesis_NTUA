import os
import csv
import json
from datetime import datetime, timezone
from typing import Optional, List
import random
from config import LOG_DIR, TARGET_URL

def parse_vegeta_metrics(report: dict) -> dict:
    def nanos_to_ms(ns):
        return round(ns / 1_000_000, 3)
    
    return {
        "throughput": report.get("throughput", 0.0),
        "avg_latency": nanos_to_ms(report.get("latencies", {}).get("mean", 0)),
        "p50_latency": nanos_to_ms(report.get("latencies", {}).get("50th", 0)),
        "p75_latency": nanos_to_ms(report.get("latencies", {}).get("75th", 0)),
        "p90_latency": nanos_to_ms(report.get("latencies", {}).get("90th", 0)),
        "p95_latency": nanos_to_ms(report.get("latencies", {}).get("95th", 0)),
        "p99_latency": nanos_to_ms(report.get("latencies", {}).get("99th", 0)),
        "max_latency": nanos_to_ms(report.get("latencies", {}).get("max", 0)),
        "min_latency": nanos_to_ms(report.get("latencies", {}).get("min", 0)),
        "errors": len(report.get("errors", []))
    }


def store_workload_metrics(csv_file: str, test_id: str, minute: int, given_rps: int, metrics: dict):
    header = [
        "Test_ID", "Minute", "Time", "RPS", "Throughput", "Avg_Latency",
        "P50_Latency", "P75_Latency", "P90_Latency", "P95_Latency",
        "P99_Latency", "Max_Latency", "Min_Latency", "Errors"
    ]

    # Check if file exists
    file_exists = os.path.exists(csv_file)

    with open(csv_file, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)

        # Write header once
        if not file_exists:
            writer.writeheader()

        # Write row
        writer.writerow({
            "Test_ID": test_id,
            "Minute": minute,
            "Time": datetime.now(timezone.utc).isoformat(),
            "RPS": given_rps,
            "Throughput": metrics.get("throughput", 0.0),
            "Avg_Latency": metrics.get("avg_latency", 0.0),
            "P50_Latency": metrics.get("p50_latency", 0.0),
            "P75_Latency": metrics.get("p75_latency", 0.0),
            "P90_Latency": metrics.get("p90_latency", 0.0),
            "P95_Latency": metrics.get("p95_latency", 0.0),
            "P99_Latency": metrics.get("p99_latency", 0.0),
            "Max_Latency": metrics.get("max_latency", 0.0),
            "Min_Latency": metrics.get("min_latency", 0.0),
            "Errors": metrics.get("errors", 0)
        })

