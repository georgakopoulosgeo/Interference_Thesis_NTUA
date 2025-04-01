#!/usr/bin/env python3
import os
import csv
import subprocess
import json

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

def start_container_monitoring(output_file: str) -> subprocess.Popen:
    """
    Start container monitoring by running docker stats in an infinite loop.
    The command outputs JSON formatted data every 5 seconds to the specified output file.
    Returns the subprocess.Popen object.
    """
    # Run docker stats in a loop using a bash command.
    cmd = [
        "bash", "-c", "while true; do docker stats --no-stream --format '{{json .}}'; sleep 5; done"
    ]
    out_file = open(output_file, "w")
    process = subprocess.Popen(cmd, stdout=out_file, stderr=subprocess.PIPE)
    return process

def collect_container_metrics(output_file: str) -> dict:
    """
    Parse the container monitoring output file and aggregate container metrics.
    Aggregates:
      - Average container CPU usage (Avg_Container_CPU)
      - Average container memory usage (Avg_Container_Mem)
      - Total disk I/O read (Disk_IO_Read) and write (Disk_IO_Write)
      - Total network I/O in (Net_IO_In) and out (Net_IO_Out)
      - Number of containers monitored (Container_Count)
    Returns a dictionary with these aggregated metrics.
    """
    if not os.path.exists(output_file):
        print(f"Container monitoring output file {output_file} does not exist.")
        return {}
    
    with open(output_file, "r") as f:
        lines = f.readlines()
    
    container_data = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            container_data.append(data)
        except Exception as e:
            print(f"Error parsing line: {line}\nError: {e}")
    
    if not container_data:
        print("No container metrics retrieved.")
        return {}
    
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
    
    avg_container_cpu = total_cpu / count if count > 0 else 0.0
    avg_container_mem = total_mem / count if count > 0 else 0.0
    
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

def store_container_metrics(csv_file: str, test_case_id: str, date_str: str, interference: str, container_metrics: dict) -> None:
    """
    Store the aggregated container metrics in a CSV file.
    The CSV includes columns:
      TestCaseID, Date, Avg_Container_CPU, Avg_Container_Mem, Container_Count,
      Disk_IO_Read, Disk_IO_Write, Net_IO_In, Net_IO_Out
    """
    header = [
        "TestCaseID",
        "Interference",
        "Date",
        "Avg_Container_CPU",
        "Avg_Container_Mem",
        "Container_Count",
        "Disk_IO_Read",
        "Disk_IO_Write",
        "Net_IO_In",
        "Net_IO_Out"
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
            "Avg_Container_CPU": container_metrics.get("avg_container_cpu", ""),
            "Avg_Container_Mem": container_metrics.get("avg_container_mem", ""),
            "Container_Count": container_metrics.get("container_count", ""),
            "Disk_IO_Read": container_metrics.get("disk_io_read", ""),
            "Disk_IO_Write": container_metrics.get("disk_io_write", ""),
            "Net_IO_In": container_metrics.get("net_io_in", ""),
            "Net_IO_Out": container_metrics.get("net_io_out", "")
        }
        writer.writerow(row)

def collect_and_store_container_metrics(output_file: str, csv_file: str, test_case_id: str, date_str: str) -> None:
    """
    Automatically collect container metrics from the output file and store them in the specified CSV file.
    """
    container_metrics = collect_container_metrics(output_file)
    store_container_metrics(csv_file, test_case_id, date_str, container_metrics)
