#!/usr/bin/env python3
import csv
import os
import re
import json

# Global header for CSV file
HEADER = [
    "TestCaseID",
    "Interference",
    "Date",
    "CPU_Utilization",       # Overall CPU usage (from AMD uProf)
    "Memory_Bandwidth",      # Memory bandwidth usage (from AMD uProf)
    "Cache_Miss_Rate",       # Percentage of cache misses (from perf)
    "CPI",                   # Cycles per instruction (from perf)
    "Page_Fault_Rate",       # Page faults count (from perf)
    "Throughput",            # Requests per second (from workload output)
    "Avg_Latency",           # Average latency in microseconds (from workload output)
    "P50_Latency",           # 50th percentile latency (microseconds)
    "P75_Latency",           # 75th percentile latency (microseconds)
    "P90_Latency",           # 90th percentile latency (microseconds)
    "P99_Latency",           # 99th percentile latency (microseconds)
    "Max_Latency",           # Maximum observed latency (microseconds)
    "Disk_IO_Read",          # Aggregated disk read in bytes (from container stats)
    "Disk_IO_Write",         # Aggregated disk write in bytes (from container stats)
    "Net_IO_In",             # Aggregated network input in bytes (from container stats)
    "Net_IO_Out",            # Aggregated network output in bytes (from container stats)
    "Avg_Container_CPU",     # Average container CPU usage (%)
    "Avg_Container_Mem",     # Average container memory usage (%)
    "Container_Count"        # Number of containers monitored
]

## Global value for Interference Type
interference_type = "None"

# ---------------------------
# Helper Functions
# ---------------------------
def convert_latency_to_us(latency_str: str) -> float:
    """
    Convert a latency string to microseconds.
    E.g., "341.52us" -> 341.52, "1.76ms" -> 1760.
    """
    latency_str = latency_str.strip()
    if latency_str.endswith("us"):
        return float(latency_str[:-2])
    elif latency_str.endswith("ms"):
        return float(latency_str[:-2]) * 1000.0
    elif latency_str.endswith("s"):
        return float(latency_str[:-1]) * 1_000_000.0
    else:
        return float(latency_str)

def parse_size(size_str: str) -> float:
    """
    Convert a human-readable size string to bytes.
    E.g., "1.2MB" -> 1.2e6, "508kB" -> 508e3, "3.833GiB" -> 3.833 * 1073741824.
    """
    size_str = size_str.strip()
    if size_str == "0B":
        return 0.0
    multipliers = {
        "B": 1,
        "kB": 1e3,
        "KB": 1e3,
        "MB": 1e6,
        "GB": 1e9,
        "GiB": 1073741824,
    }
    for unit, mult in multipliers.items():
        if size_str.endswith(unit):
            try:
                num = float(size_str[:-len(unit)])
                return num * mult
            except:
                return 0.0
    try:
        return float(size_str)
    except:
        return 0.0

# ---------------------------
# Workload Output Parsing
# ---------------------------
def parse_workload_output(output: str) -> dict:
    """
    Parse workload generator output to extract throughput and latency metrics.
    Returns a dictionary with:
      - throughput: Requests/sec (float)
      - avg_latency: Average latency in microseconds (float)
      - p50_latency, p75_latency, p90_latency, p99_latency, max_latency: in microseconds
    """
    metrics = {}
    # Throughput extraction
    for line in output.splitlines():
        if "Requests/sec:" in line:
            try:
                throughput = float(line.split(":")[-1].strip())
                metrics["throughput"] = throughput
            except:
                metrics["throughput"] = None

    # Average latency extraction from the "Thread Stats" line
    for line in output.splitlines():
        if line.strip().startswith("Latency") and "Thread Stats" not in line:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    metrics["avg_latency"] = convert_latency_to_us(parts[1])
                except:
                    metrics["avg_latency"] = None
            break

    # Extract percentiles from the latency distribution section
    latency_pattern = re.compile(r"([\d\.]+)%\s+([\d\.]+(us|ms|s))")
    for line in output.splitlines():
        match = latency_pattern.search(line)
        if match:
            percentile = float(match.group(1))
            latency_val = convert_latency_to_us(match.group(2))
            if abs(percentile - 50.0) < 1e-3:
                metrics["p50_latency"] = latency_val
            elif abs(percentile - 75.0) < 1e-3:
                metrics["p75_latency"] = latency_val
            elif abs(percentile - 90.0) < 1e-3:
                metrics["p90_latency"] = latency_val
            elif abs(percentile - 99.0) < 1e-3:
                metrics["p99_latency"] = latency_val
            elif percentile >= 100.0:
                metrics["max_latency"] = latency_val

    return metrics

# ---------------------------
# Container Metrics Parsing
# ---------------------------
def handle_container_metrics_enhanced(container_metrics_file: str) -> dict:
    """
    Collect and aggregate container metrics.
    Aggregates:
      - CPU usage, memory usage (averages)
      - BlockIO (disk read/write) and NetIO (network in/out) across all containers.
    Saves raw container data to a CSV file.
    """
    print("Collecting container metrics (enhanced)...")
    cmd = ["sudo", "docker", "stats", "--no-stream", "--format", "{{json .}}"]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running docker stats: {e}")
        return {}
    
    container_data = []
    for line in result.stdout.strip().splitlines():
        try:
            data = json.loads(line)
            container_data.append(data)
        except Exception as e:
            print(f"Error parsing docker stats line: {line}\nError: {e}")
    
    if container_data:
        keys = container_data[0].keys()
        with open(container_metrics_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in container_data:
                writer.writerow(row)
        print(f"Container metrics saved to {container_metrics_file}")
    else:
        print("No container metrics retrieved.")
    
    total_cpu = 0.0
    total_mem = 0.0
    total_disk_read = 0.0
    total_disk_write = 0.0
    total_net_in = 0.0
    total_net_out = 0.0
    count = 0
    for entry in container_data:
        count += 1
        # CPU usage (e.g., "201.14%")
        cpu_str = entry.get("CPUPerc", "").replace("%", "").strip()
        try:
            total_cpu += float(cpu_str)
        except:
            pass
        # Memory usage (e.g., "49.42%")
        mem_str = entry.get("MemPerc", "").replace("%", "").strip()
        try:
            total_mem += float(mem_str)
        except:
            pass
        # BlockIO: "X / Y" where X = read, Y = write
        block_io = entry.get("BlockIO", "0B / 0B")
        parts = block_io.split("/")
        if len(parts) == 2:
            read_str = parts[0].strip()
            write_str = parts[1].strip()
            total_disk_read += parse_size(read_str)
            total_disk_write += parse_size(write_str)
        # NetIO: "X / Y" where X = in, Y = out
        net_io = entry.get("NetIO", "0B / 0B")
        parts = net_io.split("/")
        if len(parts) == 2:
            net_in_str = parts[0].strip()
            net_out_str = parts[1].strip()
            total_net_in += parse_size(net_in_str)
            total_net_out += parse_size(net_out_str)
    
    avg_container_cpu = total_cpu / count if count > 0 else ""
    avg_container_mem = total_mem / count if count > 0 else ""
    aggregated = {
        "avg_container_cpu": avg_container_cpu,
        "avg_container_mem": avg_container_mem,
        "container_count": count,
        "disk_io_read": total_disk_read,
        "disk_io_write": total_disk_write,
        "net_io_in": total_net_in,
        "net_io_out": total_net_out
    }
    return aggregated

# ---------------------------
# Perf Metrics Parsing
# ---------------------------
def parse_perf_results(perf_raw_file: str) -> dict:
    metrics = {}
    with open(perf_raw_file, "r") as f:
        for line in f:
            if "cycles" in line and "instructions" not in line:
                try:
                    metrics["cycles"] = int(line.split()[0].replace(",", ""))
                except:
                    metrics["cycles"] = 0
            elif "instructions" in line:
                try:
                    metrics["instructions"] = int(line.split()[0].replace(",", ""))
                except:
                    metrics["instructions"] = 0
            elif "cache-references" in line:
                try:
                    metrics["cache_references"] = int(line.split()[0].replace(",", ""))
                except:
                    metrics["cache_references"] = 0
            elif "cache-misses" in line:
                try:
                    metrics["cache_misses"] = int(line.split()[0].replace(",", ""))
                except:
                    metrics["cache_misses"] = 0
            elif "page-faults" in line:
                try:
                    metrics["page_faults"] = int(line.split()[0].replace(",", ""))
                except:
                    metrics["page_faults"] = 0
    return metrics

def handle_perf_results(perf_raw_file: str) -> dict:
    perf_metrics = parse_perf_results(perf_raw_file)
    if "cycles" in perf_metrics and "instructions" in perf_metrics and perf_metrics["instructions"] != 0:
        cpi = perf_metrics["cycles"] / perf_metrics["instructions"]
    else:
        cpi = ""
    if "cache_misses" in perf_metrics and "cache_references" in perf_metrics and perf_metrics["cache_references"] != 0:
        cache_miss_rate = (perf_metrics["cache_misses"] / perf_metrics["cache_references"]) * 100
    else:
        cache_miss_rate = ""
    page_fault_rate = perf_metrics.get("page_faults", "")
    return {"cpi": cpi, "cache_miss_rate": cache_miss_rate, "page_fault_rate": page_fault_rate}

# ---------------------------
# AMD uProf Metrics Parsing
# ---------------------------
def parse_amduprof_results(amduprof_raw_file: str) -> dict:
    metrics = {}
    with open(amduprof_raw_file, "r") as f:
        for line in f:
            if "CPU Utilization" in line:
                try:
                    metrics["cpu_utilization"] = float(line.split(":")[1].strip().replace("%", ""))
                except:
                    metrics["cpu_utilization"] = ""
            elif "Memory Bandwidth" in line:
                try:
                    parts = line.split(":")[1].strip().split()
                    metrics["memory_bandwidth"] = float(parts[0])
                except:
                    metrics["memory_bandwidth"] = ""
    return metrics

def handle_amduprof_results(amduprof_raw_file: str) -> dict:
    amduprof_metrics = parse_amduprof_results(amduprof_raw_file)
    return {
        "cpu_utilization": amduprof_metrics.get("cpu_utilization", ""),
        "memory_bandwidth": amduprof_metrics.get("memory_bandwidth", "")
    }

# ---------------------------
# CSV Storage Function
# ---------------------------
def store_results_in_csv(results_csv: str, test_case_id: str, date_str: str,
                         metrics_perf: dict, metrics_amd: dict,
                         metrics_workload: dict, metrics_container: dict):
    file_exists = os.path.exists(results_csv)
    with open(results_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if not file_exists:
            writer.writeheader()
        row = {
            "TestCaseID": test_case_id,
            "Interference": interference_type,
            "Date": date_str,
            "CPU_Utilization": metrics_amd.get("cpu_utilization", ""),
            "Memory_Bandwidth": metrics_amd.get("memory_bandwidth", ""),
            "Cache_Miss_Rate": metrics_perf.get("cache_miss_rate", ""),
            "CPI": metrics_perf.get("cpi", ""),
            "Page_Fault_Rate": metrics_perf.get("page_fault_rate", ""),
            "Throughput": metrics_workload.get("throughput", ""),
            "Avg_Latency": metrics_workload.get("avg_latency", ""),
            "P50_Latency": metrics_workload.get("p50_latency", ""),
            "P75_Latency": metrics_workload.get("p75_latency", ""),
            "P90_Latency": metrics_workload.get("p90_latency", ""),
            "P99_Latency": metrics_workload.get("p99_latency", ""),
            "Max_Latency": metrics_workload.get("max_latency", ""),
            "Disk_IO_Read": metrics_container.get("disk_io_read", ""),
            "Disk_IO_Write": metrics_container.get("disk_io_write", ""),
            "Net_IO_In": metrics_container.get("net_io_in", ""),
            "Net_IO_Out": metrics_container.get("net_io_out", ""),
            "Avg_Container_CPU": metrics_container.get("avg_container_cpu", ""),
            "Avg_Container_Mem": metrics_container.get("avg_container_mem", ""),
            "Container_Count": metrics_container.get("container_count", "")
        }
        writer.writerow(row)

