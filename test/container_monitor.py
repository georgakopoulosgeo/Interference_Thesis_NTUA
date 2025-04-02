#!/usr/bin/env python3
import requests
import csv
import datetime
import time

# Global configuration
PROMETHEUS_URL = "http://localhost:9090"
STEP = "5"  # 5-second resolution

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
            # Use container_name as the identifier; adjust if you use a different label.
            cid = result["metric"].get("container_name", "unknown")
            results.setdefault(cid, []).extend(result["values"])
    else:
        print("Prometheus query failed:", data)
    return results

def merge_metric(metric_name, metric_data, detailed_data):
    """
    Merge a specific metric’s data into the detailed_data dictionary.
    detailed_data is a nested dictionary keyed first by container ID then by timestamp.
    """
    for cid, values in metric_data.items():
        for ts, val in values:
            # Convert the timestamp (seconds since epoch) to a human-readable string.
            ts_str = datetime.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
            if ts_str not in detailed_data.setdefault(cid, {}):
                detailed_data[cid][ts_str] = {}
            detailed_data[cid][ts_str][metric_name] = float(val)

def collect_container_metrics(prom_url, start_time, end_time, step, test_case_id, interference, date_str, detail_csv_path, agg_csv_path):
    """
    Collect container metrics from Prometheus between start_time and end_time,
    then store both detailed and aggregated metrics in CSV files.
    
    The following PromQL queries are used (filtering by the label for your social network app):
      - CPU usage: rate(container_cpu_usage_seconds_total[5s])
      - Memory usage: container_memory_usage_bytes
      - Disk I/O (read/write): rate(container_fs_reads_bytes_total[5s]) and rate(container_fs_writes_bytes_total[5s])
      - Network I/O (in/out): rate(container_network_receive_bytes_total[5s]) and rate(container_network_transmit_bytes_total[5s])
    """
    # Define the queries – adjust label filters as necessary.
    query_cpu = 'rate(container_cpu_usage_seconds_total{container_label_com_docker_swarm_service_name="socialnetwork_app"}[5s])'
    query_mem = 'container_memory_usage_bytes{container_label_com_docker_swarm_service_name="socialnetwork_app"}'
    query_disk_read = 'rate(container_fs_reads_bytes_total{container_label_com_docker_swarm_service_name="socialnetwork_app"}[5s])'
    query_disk_write = 'rate(container_fs_writes_bytes_total{container_label_com_docker_swarm_service_name="socialnetwork_app"}[5s])'
    query_net_in = 'rate(container_network_receive_bytes_total{container_label_com_docker_swarm_service_name="socialnetwork_app"}[5s])'
    query_net_out = 'rate(container_network_transmit_bytes_total{container_label_com_docker_swarm_service_name="socialnetwork_app"}[5s])'
    
    # Query Prometheus for each metric over the experiment window.
    cpu_data = query_range(query_cpu, start_time, end_time, step)
    mem_data = query_range(query_mem, start_time, end_time, step)
    disk_read_data = query_range(query_disk_read, start_time, end_time, step)
    disk_write_data = query_range(query_disk_write, start_time, end_time, step)
    net_in_data = query_range(query_net_in, start_time, end_time, step)
    net_out_data = query_range(query_net_out, start_time, end_time, step)
    
    # Merge the data from all queries into a detailed data structure.
    detailed_data = {}
    merge_metric("cpu", cpu_data, detailed_data)
    merge_metric("mem", mem_data, detailed_data)
    merge_metric("disk_read", disk_read_data, detailed_data)
    merge_metric("disk_write", disk_write_data, detailed_data)
    merge_metric("net_in", net_in_data, detailed_data)
    merge_metric("net_out", net_out_data, detailed_data)
    
    # Write detailed CSV file.
    # Columns: TestCaseID, Interference, Date, Timestamp, Container_ID, CPU_Usage, Memory_Usage, Disk_IO_Read, Disk_IO_Write, Net_IO_In, Net_IO_Out
    with open(detail_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["TestCaseID", "Interference", "Date", "Timestamp", "Container_ID",
                         "CPU_Usage", "Memory_Usage", "Disk_IO_Read", "Disk_IO_Write", "Net_IO_In", "Net_IO_Out"])
        for cid in sorted(detailed_data.keys()):
            for ts in sorted(detailed_data[cid].keys()):
                metrics = detailed_data[cid][ts]
                writer.writerow([test_case_id, interference, date_str, ts, cid,
                                 metrics.get("cpu", ""),
                                 metrics.get("mem", ""),
                                 metrics.get("disk_read", ""),
                                 metrics.get("disk_write", ""),
                                 metrics.get("net_in", ""),
                                 metrics.get("net_out", "")])
    
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
            if "cpu" in metrics:
                cpu_vals.append(metrics["cpu"])
            if "mem" in metrics:
                mem_vals.append(metrics["mem"])
            if "disk_read" in metrics:
                disk_read_vals.append(metrics["disk_read"])
            if "disk_write" in metrics:
                disk_write_vals.append(metrics["disk_write"])
            if "net_in" in metrics:
                net_in_vals.append(metrics["net_in"])
            if "net_out" in metrics:
                net_out_vals.append(metrics["net_out"])
        agg_data[cid] = {
            "avg_cpu": sum(cpu_vals)/len(cpu_vals) if cpu_vals else None,
            "avg_mem": sum(mem_vals)/len(mem_vals) if mem_vals else None,
            "avg_disk_read": sum(disk_read_vals)/len(disk_read_vals) if disk_read_vals else None,
            "avg_disk_write": sum(disk_write_vals)/len(disk_write_vals) if disk_write_vals else None,
            "avg_net_in": sum(net_in_vals)/len(net_in_vals) if net_in_vals else None,
            "avg_net_out": sum(net_out_vals)/len(net_out_vals) if net_out_vals else None,
        }
    
    # Write aggregated CSV file.
    # Columns: TestCaseID, Interference, Date, Container_ID, Avg_CPU_Usage, Avg_Memory_Usage, Avg_Disk_IO_Read, Avg_Disk_IO_Write, Avg_Net_IO_In, Avg_Net_IO_Out
    with open(agg_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["TestCaseID", "Interference", "Date", "Container_ID",
                         "Avg_CPU_Usage", "Avg_Memory_Usage", "Avg_Disk_IO_Read", "Avg_Disk_IO_Write", "Avg_Net_IO_In", "Avg_Net_IO_Out"])
        for cid in sorted(agg_data.keys()):
            agg = agg_data[cid]
            writer.writerow([test_case_id, interference, date_str, cid,
                             agg["avg_cpu"], agg["avg_mem"], agg["avg_disk_read"],
                             agg["avg_disk_write"], agg["avg_net_in"], agg["avg_net_out"]])
    
    print(f"Detailed metrics stored in {detail_csv_path}")
    print(f"Aggregated metrics stored in {agg_csv_path}")

'''
# Example usage:
# In practice, your coordinator will call collect_container_metrics() after workload completion,
# passing the correct epoch timestamps as strings.
if __name__ == "__main__":
    test_case_id = "Test01"
    interference = "None"
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # For demonstration, assume the workload ran for 2 minutes.
    # In your experiment, record the precise start and end timestamps.
    end_time = time.time() - 60   # Ended 1 minute ago
    start_time = end_time - 120   # 2-minute duration
    start_time_str = str(start_time)
    end_time_str = str(end_time)
    
    detail_csv_path = f"container_metrics_detail_{test_case_id}_{date_str}.csv"
    agg_csv_path = f"container_metrics_agg_{test_case_id}_{date_str}.csv"

'''