#!/usr/bin/env python3
import subprocess
import csv
import os

def run_combined_perf(duration: int, interval: int, output_csv: str) -> None:
    """
    Run a single perf command that collects:
      - Memory traffic counters:
          ls_dmnd_fills_from_sys.mem_io_local,
          ls_hw_pf_dc_fills.mem_io_local,
          ls_sw_pf_dc_fills.mem_io_local,
          ls_dispatch.store_dispatch
      - IPC and cache misses:
          instructions, cpu-cycles, cache-misses
      - Disk I/O related (indirectly via faults):
          page-faults, major-faults
    Data is sampled every 'interval' milliseconds, for a total of 'duration' seconds.
    The results are output in CSV format to output_csv.
    """
    # Combine all events into a single comma separated string
    events = (
        "task-clock,"
        "branches,"
        "branch-instructions,"
        "branch-misses,"
        "stalled-cycles-frontend,"
        "stalled-cycles-backend,"
        "bus-cycles,"
        "cache-references,"
        "cache-misses,"
        "LLC-loads,"
        "LLC-load-misses,"
        "LLC-stores,"
        "LLC-store-misses,"
        "cycle_activity.stalls_l3_miss,"
        "mem-loads,"
        "mem-stores,"
        "dtlb_load_misses.stlb_hit,"
        "page-faults"
    )
    cmd = [
        "perf", "stat", "--csv",
        "-I", str(interval),
        "-e", events,
        "-a",  # system-wide measurement
        "-o", output_csv,
        "sleep", str(duration)
    ]
    # Start the perf command; its output will be directed to output_csv
    print("Perf: Executing command:", " ".join(cmd))
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Perf: perf stat finished with return code:", process.returncode)
    if process.stdout:
        print("Perf: stdout:", process.stdout)
    if process.stderr:
        print("Perf: stderr:", process.stderr)

def parse_perf_csv(raw_file: str, output_csv: str) -> None:
    """
    Parse a raw perf output text file and produce a CSV file where each row corresponds
    to a unique timestamp and contains the counts for each event.e"
    """

    # Define the order of events we expect (excluding the time column)
    events_order = [
        "task-clock",
        "branches",
        "branch-instructions",
        "branch-misses",
        "stalled-cycles-frontend",
        "stalled-cycles-backend",
        "bus-cycles",
        "cache-references",
        "cache-misses",
        "LLC-loads",
        "LLC-load-misses",
        "LLC-stores",
        "LLC-store-misses",
        "cycle_activity.stalls_l3_miss",
        "mem-loads",
        "mem-stores",
        "dtlb_load_misses.stlb_hit",
        "page-faults"
    ]
    
    samples = []       # List to hold each sample as a dictionary.
    current_timestamp = None
    current_sample = {}

    with open(raw_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # Skip blank and comment lines
            # Split the line into parts. We expect at least three parts:
            # time, count, event_name. Extra tokens (like comments) will be ignored.
            parts = line.split()
            if len(parts) < 3:
                continue

            try:
                timestamp = float(parts[0])
                count = int(parts[1].replace(",", ""))
            except Exception:
                continue  # Skip lines that do not conform

            # Assume the event name is the third token.
            event_name = parts[2]
            
            # If the timestamp changes, it means a new sample has started.
            if current_timestamp is None:
                current_timestamp = timestamp
                current_sample = {"time": timestamp}
            elif abs(timestamp - current_timestamp) > 1e-6:
                samples.append(current_sample)
                current_timestamp = timestamp
                current_sample = {"time": timestamp}

            # Record the event count in the current sample.
            current_sample[event_name] = count

        # Append the final sample if available.
        if current_sample:
            samples.append(current_sample)

    # Write the collected samples to the output CSV file.
    header = ["time"] + events_order
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        for sample in samples:
            row = {"time": sample.get("time", "")}
            for event in events_order:
                row[event] = sample.get(event, "")
            writer.writerow(row)


def perf_monitoring(duration: int, interval: int, raw_file: str, output_csv: str):
    # Parameters: 10-second duration, 5000ms (5 sec) sampling interval, and output file name
    # duration = 10
    # interval = 5000

    print("Perf: Starting monitoring ...")
    run_combined_perf(duration, interval, raw_file)
    # You can later run this in a separate thread or process as required.
    # perf_process.wait()  # Wait for the perf command to complete

    print("Perf: Parsing results...")
    metrics = parse_perf_csv(raw_file, output_csv)
    print("Perf: Completed.")