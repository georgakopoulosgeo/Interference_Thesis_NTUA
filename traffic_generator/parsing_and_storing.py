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
        "Test_ID", "Minute", "RPS", "Throughput", "Avg_Latency",
        "P50_Latency", "P75_Latency", "P90_Latency", "P95_Latency",
        "P99_Latency", "Max_Latency", "Min_Latency", "Errors"
    ]
    file_exists = os.path.exists(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        row = {
            "Test_ID": test_id,
            "Minute": minute,
            "RPS": given_rps,
            "Throughput": metrics["throughput"],
            "Avg_Latency": metrics["avg_latency"],
            "P50_Latency": metrics["p50_latency"],
            "P75_Latency": metrics["p75_latency"],
            "P90_Latency": metrics["p90_latency"],
            "P95_Latency": metrics["p95_latency"],
            "P99_Latency": metrics["p99_latency"],
            "Max_Latency": metrics["max_latency"],
            "Min_Latency": metrics["min_latency"],
            "Errors": metrics["errors"]
        }
        writer.writerow(row)
