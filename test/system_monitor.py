#!/usr/bin/env python3
import os
import csv
import subprocess

def start_perf_monitoring(duration: int, perf_raw_file: str) -> subprocess.Popen:
    """
    Start perf monitoring for the given duration.
    Output is redirected to the specified perf_raw_file.
    """
    cmd = [
        "perf", "stat",
        "-e", "cycles,instructions,cache-references,cache-misses,page-faults",
        "--", "sleep", str(duration)
    ]
    return subprocess.Popen(cmd, stderr=open(perf_raw_file, "w"))

def start_amduprof_monitoring(duration: int, amduprof_raw_file: str) -> subprocess.Popen:
    """
    Start AMD uProf monitoring for the given duration.
    Output is redirected to the specified amduprof_raw_file.
    """
    cmd = [
        "/opt/AMDuProf_5.0-1479/bin/AMDuProfCLI",
        "collect",
        "--trace", "-osrt",
        "osrt-event", "diskio",
        "-o", "/tmp/testamd/",
        "-a",
        "--duration", str(duration),
    ]
    return subprocess.Popen(cmd, stdout=open(amduprof_raw_file, "w"), stderr=subprocess.PIPE)

def handle_perf_results(perf_raw_file: str) -> dict:
    """
    Parse the perf raw output file to extract relevant metrics and compute derived metrics.
    Returns a dictionary containing:
      - CPI (cycles per instruction)
      - Cache_Miss_Rate (percentage)
      - Page_Fault_Rate (raw count)
    """
    perf_metrics = {}
    with open(perf_raw_file, "r") as f:
        for line in f:
            if "cycles" in line and "instructions" not in line:
                try:
                    perf_metrics["cycles"] = int(line.split()[0].replace(",", ""))
                except:
                    perf_metrics["cycles"] = 0
            elif "instructions" in line:
                try:
                    perf_metrics["instructions"] = int(line.split()[0].replace(",", ""))
                except:
                    perf_metrics["instructions"] = 0
            elif "cache-references" in line:
                try:
                    perf_metrics["cache_references"] = int(line.split()[0].replace(",", ""))
                except:
                    perf_metrics["cache_references"] = 0
            elif "cache-misses" in line:
                try:
                    perf_metrics["cache_misses"] = int(line.split()[0].replace(",", ""))
                except:
                    perf_metrics["cache_misses"] = 0
            elif "page-faults" in line:
                try:
                    perf_metrics["page_faults"] = int(line.split()[0].replace(",", ""))
                except:
                    perf_metrics["page_faults"] = 0

    cpi = ""
    if perf_metrics.get("instructions", 0) != 0:
        cpi = perf_metrics.get("cycles", 0) / perf_metrics.get("instructions", 1)
    cache_miss_rate = ""
    if perf_metrics.get("cache_references", 0) != 0:
        cache_miss_rate = (perf_metrics.get("cache_misses", 0) / perf_metrics.get("cache_references", 1)) * 100
    page_fault_rate = perf_metrics.get("page_faults", "")

    return {"cpi": cpi, "cache_miss_rate": cache_miss_rate, "page_fault_rate": page_fault_rate}

def handle_amduprof_results(amduprof_raw_file: str) -> dict:
    """
    Parse the AMD uProf raw output file to extract system-level metrics.
    Returns a dictionary containing:
      - CPU_Utilization (in percentage)
      - Memory_Bandwidth (in appropriate units)
    """
    amduprof_metrics = {}
    with open(amduprof_raw_file, "r") as f:
        for line in f:
            if "CPU Utilization" in line:
                try:
                    amduprof_metrics["cpu_utilization"] = float(line.split(":")[1].strip().replace("%", ""))
                except:
                    amduprof_metrics["cpu_utilization"] = ""
            elif "Memory Bandwidth" in line:
                try:
                    parts = line.split(":")[1].strip().split()
                    amduprof_metrics["memory_bandwidth"] = float(parts[0])
                except:
                    amduprof_metrics["memory_bandwidth"] = ""
    return amduprof_metrics

def wait_for_monitors(perf_process: subprocess.Popen, amduprof_process: subprocess.Popen) -> None:
    """
    Wait for both perf and AMD uProf monitoring processes to complete.
    """
    perf_process.wait()
    amduprof_process.wait()

def collect_and_store_system_metrics(perf_raw_file: str, amduprof_raw_file: str, csv_file: str,
                                       test_case_id: str, date_str: str, interference: str) -> None:
    """
    Automatically collect system metrics from the raw monitoring files,
    merge them, and store them into the specified CSV file.
    """
    system_perf_metrics = handle_perf_results(perf_raw_file)
    system_amduprof_metrics = handle_amduprof_results(amduprof_raw_file)
    system_metrics = {**system_perf_metrics, **system_amduprof_metrics}
    store_system_metrics(csv_file, test_case_id, date_str, interference, system_metrics)


def store_system_metrics(csv_file: str, test_case_id: str, date_str: str, interference: str, system_metrics: dict) -> None:
    """
    Store the system monitoring metrics in a CSV file.
    The CSV includes the following columns:
      TestCaseID, Interference, Date, CPU_Utilization, Memory_Bandwidth, Cache_Miss_Rate, CPI, Page_Fault_Rate
    """
    header = [
        "TestCaseID",
        "Interference",
        "Date",
        "CPU_Utilization",
        "Memory_Bandwidth",
        "Cache_Miss_Rate",
        "CPI",
        "Page_Fault_Rate"
    ]
    file_exists = os.path.exists(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        row = {
            "TestCaseID": test_case_id,
            "Interference": interference,
            "Date": date_str,
            "CPU_Utilization": system_metrics.get("cpu_utilization", ""),
            "Memory_Bandwidth": system_metrics.get("memory_bandwidth", ""),
            "Cache_Miss_Rate": system_metrics.get("cache_miss_rate", ""),
            "CPI": system_metrics.get("cpi", ""),
            "Page_Fault_Rate": system_metrics.get("page_fault_rate", "")
        }
        writer.writerow(row)
