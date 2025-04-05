#!/usr/bin/env python3
import requests
import csv
import datetime
import time

# Global configuration
PROMETHEUS_URL = "http://localhost:9090"
STEP = "10"  # 5-second resolution
container_names = {} # Global dictionary to store container names for each container ID

def query_range(query, start_time, end_time, step):
    """
    Query the Prometheus API for a given PromQL query over the specified time range.
    Returns a dictionary keyed by container ID, each with a list of (timestamp, value) pairs.
    """
    url = f"{PROMETHEUS_URL}/api/v1/query_range"
    params = {
        "query": query,
        "start": start_time,
        "end": end_time,
        "step": step
    }
    response = requests.get(url, params=params)
    data = response.json()
    results = {}
    if data["status"] == "success":
        for result in data["data"]["result"]:
            # Use container id if available; fallback to container_name
            cid = result["metric"].get("id") or result["metric"].get("container_name", "unknown")
            # cid has the form "/system.slice/docker-00f86d51cc143710c51b51edf34266d16c23204df72b47e1509c4b8cc34d817e.scope"
            # Extract the container ID from the end of the string
            cid = cid.split("/")[-1].split(".scope")[0]
            cid = cid.split("-")[-1]
            container_names[cid] = result["metric"].get("name", "unknown")
            # Prometheus returns a list of (timestamp, value) pairs in "values"
            for ts_value in result["values"]:
                ts = ts_value[0]  # timestamp as string (seconds since epoch)
                value = ts_value[1]
                results.setdefault(cid, []).append((ts, value))
    else:
        print("Prometheus query failed:", data)
    return results

def merge_metric(metric_name, metric_data, detailed_data):
    """
    Merge a specific metric’s data into the detailed_data dictionary.
    detailed_data is a nested dictionary keyed first by container ID then by a formatted timestamp.
    """
    for cid, values in metric_data.items():
        for ts, val in values:
            # Convert the timestamp to a human-readable string.
            ts_float = float(ts)
            ts_str = datetime.datetime.fromtimestamp(ts_float).strftime("%Y-%m-%d %H:%M:%S")
            if cid not in detailed_data:
                detailed_data[cid] = {}
            if ts_str not in detailed_data[cid]:
                detailed_data[cid][ts_str] = {}
            try:
                detailed_data[cid][ts_str][metric_name] = float(val)
            except ValueError:
                detailed_data[cid][ts_str][metric_name] = None

def collect_container_metrics(prom_url, start_time, end_time, step, test_case_id, interference, date_str, detail_csv_path, agg_csv_path):
    """
    Collect container metrics from Prometheus between start_time and end_time,
    then store both detailed and aggregated metrics in CSV files.
    
    The following PromQL queries are used (filtering by the label for your socialnetwork_app):
      - CPU usage: rate(container_cpu_usage_seconds_total[5s])
      - Memory usage: container_memory_usage_bytes
      - Disk I/O (read/write): rate(container_fs_reads_bytes_total[5s]) and rate(container_fs_writes_bytes_total[5s])
      - Network I/O (in/out): rate(container_network_receive_bytes_total[5s]) and rate(container_network_transmit_bytes_total[5s])
    """
    # Define the queries – adjust label filters as necessary.
    query_cpu = 'rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_project="socialnetwork_app"}[5s])'
    query_mem = 'container_memory_usage_bytes{container_label_com_docker_compose_project="socialnetwork_app"}'
    query_disk_read = 'rate(container_fs_reads_bytes_total{container_label_com_docker_compose_project="socialnetwork_app"}[5s])'
    query_disk_write = 'rate(container_fs_writes_bytes_total{container_label_com_docker_compose_project="socialnetwork_app"}[5s])'
    query_net_in = 'rate(container_network_receive_bytes_total{container_label_com_docker_compose_project="socialnetwork_app"}[5s])'
    query_net_out = 'rate(container_network_transmit_bytes_total{container_label_com_docker_compose_project="socialnetwork_app"}[5s])'
    
    # Query Prometheus for each metric over the experiment window.
    cpu_data = query_range(query_cpu, start_time, end_time, step)
    mem_data = query_range(query_mem, start_time, end_time, step)
    disk_read_data = query_range(query_disk_read, start_time, end_time, step)
    disk_write_data = query_range(query_disk_write, start_time, end_time, step)
    net_in_data = query_range(query_net_in, start_time, end_time, step)
    net_out_data = query_range(query_net_out, start_time, end_time, step)
    
    # Merge the data from all queries into a detailed data structure.
    detailed_data = {}
    merge_metric("CPU_Usage", cpu_data, detailed_data)
    merge_metric("Memory_Usage", mem_data, detailed_data)
    merge_metric("Disk_IO_Read", disk_read_data, detailed_data)
    merge_metric("Disk_IO_Write", disk_write_data, detailed_data)
    merge_metric("Net_IO_In", net_in_data, detailed_data)
    merge_metric("Net_IO_Out", net_out_data, detailed_data)
    
    # Write detailed CSV file.
    # Columns: TestCaseID, Interference, Date, Timestamp, Container_ID,
    # CPU_Usage, Memory_Usage, Disk_IO_Read, Disk_IO_Write, Net_IO_In, Net_IO_Out
    with open(detail_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["TestCaseID", "Interference", "Date", "Timestamp", "Container_ID", "Container_Name",
                         "CPU_Usage", "Memory_Usage", "Disk_IO_Read", "Disk_IO_Write", "Net_IO_In", "Net_IO_Out"])
        for cid in sorted(detailed_data.keys()):
            for ts in sorted(detailed_data[cid].keys()):
                cname = container_names.get(cid, "unknown")
                metrics = detailed_data[cid][ts]
                writer.writerow([test_case_id, interference, date_str, ts, cid, cname,
                                 metrics.get("CPU_Usage", ""),
                                 metrics.get("Memory_Usage", ""),
                                 metrics.get("Disk_IO_Read", ""),
                                 metrics.get("Disk_IO_Write", ""),
                                 metrics.get("Net_IO_In", ""),
                                 metrics.get("Net_IO_Out", "")])
    
    # Compute aggregated metrics for each container.
    agg_data = {}
    for cid, ts_data in detailed_data.items():
        cpu_vals = []
        mem_vals = []
        disk_read_vals = []
        disk_write_vals = []
        net_in_vals = []
        net_out_vals = []
        for ts, metrics in ts_data.items():
            if "CPU_Usage" in metrics:
                cpu_vals.append(metrics["CPU_Usage"])
            if "Memory_Usage" in metrics:
                mem_vals.append(metrics["Memory_Usage"])
            if "Disk_IO_Read" in metrics:
                disk_read_vals.append(metrics["Disk_IO_Read"])
            if "Disk_IO_Write" in metrics:
                disk_write_vals.append(metrics["Disk_IO_Write"])
            if "Net_IO_In" in metrics:
                net_in_vals.append(metrics["Net_IO_In"])
            if "Net_IO_Out" in metrics:
                net_out_vals.append(metrics["Net_IO_Out"])
        agg_data[cid] = {
            "Avg_CPU_Usage": sum(cpu_vals)/len(cpu_vals) if cpu_vals else None,
            "Avg_Memory_Usage": sum(mem_vals)/len(mem_vals) if mem_vals else None,
            "Avg_Disk_IO_Read": sum(disk_read_vals)/len(disk_read_vals) if disk_read_vals else None,
            "Avg_Disk_IO_Write": sum(disk_write_vals)/len(disk_write_vals) if disk_write_vals else None,
            "Avg_Net_IO_In": sum(net_in_vals)/len(net_in_vals) if net_in_vals else None,
            "Avg_Net_IO_Out": sum(net_out_vals)/len(net_out_vals) if net_out_vals else None,
        }
    
    # Write aggregated CSV file.
    # Columns: TestCaseID, Interference, Date, Container_ID, Avg_CPU_Usage, Avg_Memory_Usage,
    # Avg_Disk_IO_Read, Avg_Disk_IO_Write, Avg_Net_IO_In, Avg_Net_IO_Out
    with open(agg_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["TestCaseID", "Interference", "Date", "Container_ID", "Container_Name",
                         "Avg_CPU_Usage", "Avg_Memory_Usage", "Avg_Disk_IO_Read", "Avg_Disk_IO_Write",
                         "Avg_Net_IO_In", "Avg_Net_IO_Out"])
        for cid in sorted(agg_data.keys()):
            cname = container_names.get(cid, "unknown")
            agg = agg_data[cid]
            writer.writerow([test_case_id, interference, date_str, cid, cname,
                             agg["Avg_CPU_Usage"], agg["Avg_Memory_Usage"], agg["Avg_Disk_IO_Read"],
                             agg["Avg_Disk_IO_Write"], agg["Avg_Net_IO_In"], agg["Avg_Net_IO_Out"]])
    
    print(f"Detailed metrics stored in {detail_csv_path}")
    print(f"Aggregated metrics stored in {agg_csv_path}")
