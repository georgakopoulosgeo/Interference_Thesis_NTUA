#!/usr/bin/env python3
import subprocess
import csv
import os
import sys

def run_pcm(duration: int, interval: int, output_csv: str) -> None:
    """
    Execute the Intel PCM tool for a given duration with a given sampling interval.
    The PCM tool is expected to output a CSV file.
    
    Parameters:
      duration: Total duration in seconds for which PCM should run.
      interval: Sampling interval in seconds (e.g., 300 for 5 minutes per sample).
      output_csv: Filename for the raw PCM CSV output.
    """
    # If output_csv does not exist, create it.
    if not os.path.exists(output_csv):
        with open(output_csv, 'w') as f:
            f.write("")

    # Go to the directory where the PCM tool is located.
    pcm_dir = "/home/george/Workspace/pcm/build/bin"
    os.chdir(pcm_dir)
    cmd = ["sudo", "./pcm", str(interval), "-csv=" + output_csv]
    print("Executing PCM command:", " ".join(cmd))
    try:
        subprocess.run(cmd, timeout=duration, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except subprocess.TimeoutExpired:
        print("PCM monitoring completed: duration reached.")
    except subprocess.CalledProcessError as e:
        print(f"Error running PCM: {e}")
    print("PCM monitoring finished. Output written to", output_csv)
    # Return to the original directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

def filter_csv_by_domain(raw_file: str, output_csv: str, domain_filter: str, desired_keywords: list) -> None:
    """
    Filters a raw PCM CSV file (with two header rows) based on the domain_filter.
    
    Parameters:
      raw_file: The raw CSV file produced by PCM.
      output_csv: The output file to write the filtered CSV.
      domain_filter: String to look for in the first header row (e.g., "system" or "core").
      desired_keywords: A list of keywords (in lower-case) to match within the metric header.
                        "date" and "time" are always included.
                        
    The filtering logic:
      - Always include a column if its metric header (second row) is "date" or "time".
      - Otherwise, include the column if:
            (a) the domain header (first row) contains the domain_filter, and
            (b) the metric header (second row) contains at least one of the desired_keywords.
    """
    with open(raw_file, mode='r', newline='') as infile:
            reader = csv.reader(infile)
            header_domain = next(reader)  # first header row: domains (e.g., System, Socket, Core)
            header_metric = next(reader)  # second header row: metric names (e.g., Date, IPC, L2MISS, etc.)
            
            # Prepare lists of indices to keep.
            indices_to_keep = []
            for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
                met_lower = met.strip().lower()
                dom_lower = dom.strip().lower()
                # Always include if the metric is "date" or "time"
                if met_lower in ("date", "time"):
                    indices_to_keep.append(idx)
                else:
                    # Check if the metric contains any desired keyword.
                    include_metric = any(kw in met_lower for kw in desired_keywords)
                    # Only include if the metric matches and the domain header contains the domain_filter.
                    if include_metric and (domain_filter in dom_lower):
                        indices_to_keep.append(idx)

            if not indices_to_keep:
                print(f"No columns matched for domain filter '{domain_filter}' with the desired keywords.")
                return

            # Write filtered data: combine first two header rows and include all subsequent rows.
            with open(output_csv, mode='w', newline='') as outfile:
                writer = csv.writer(outfile)
                # Combine first two header rows
                combined_header = [f"{header_domain[i]} - {header_metric[i]}" for i in indices_to_keep]
                writer.writerow(combined_header)
                # Write the rest of the data
                for row in reader:
                    filtered_row = [row[i] for i in indices_to_keep]
                    writer.writerow(filtered_row)
            print(f"Filtered CSV written to {output_csv} using domain filter '{domain_filter}'.")

def pcm_monitoring(duration: int, interval: int, raw_csv: str, system_csv: str, core_csv: str) -> None:
    # Configuration parameters
    #total_duration = 3600         # e.g., 3600 sec = 1 hour
    #sampling_interval = 300       # 300 sec = 5 minutes per sample
    #raw_csv_file = "pcm_raw_output.csv"
    #system_csv_file = "pcm_system_filtered.csv"
    #core_csv_file = "pcm_core_filtered.csv"

    # If interval in ms, convert to seconds
    if interval > 1000:
        interval = interval / 1000
    
    # Desired keywords in metric header (in lower-case)
    desired_keywords = [
        "ipc",
        "l2miss",
        "l3miss",
        "read",
        "write",
        "c0res%",
        "c1res%",
        "c6res%"
    ]
    
    print("Starting PCM monitoring...")
    run_pcm(duration, interval, raw_csv)
    print("PCM monitoring finished. Now filtering CSV data...")

    # Create filtered file for system-level data (domain header contains "system")
    filter_csv_by_domain(raw_csv, system_csv, "system", desired_keywords)
    
    # Create filtered file for core-level data (domain header contains "core")
    filter_csv_by_domain(raw_csv, core_csv, "core", desired_keywords)
    
    print("Filtering complete. Check the output files for system and core metrics.")
