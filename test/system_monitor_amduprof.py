#!/usr/bin/env python3
import subprocess
import csv
import os
import threading

def run_amduprof(duration: int, sampling_interval: int, output_csv: str) -> None:
    """
    Runs the AMD uProf PCM command to collect metrics for the given duration.
    Sampling interval is in milliseconds.
    """
    cmd = [
        "sudo", "/opt/AMDuProf_5.0-1479/bin/AMDuProfPcm", 
        "-m", "ipc,l2",
        "-a",
        "-A", "system",
        "-d", str(duration),
        "-I", str(sampling_interval),
        "-o", output_csv
    ]
    print("AMDuProf: Executing command:", " ".join(cmd))
    # Execute the command and wait for it to complete.
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("AMDuProf: AMDuProfPcm finished with return code:", process.returncode)
    if process.stdout:
        print("AMDuProf: stdout:", process.stdout)
    if process.stderr:
        print("AMDuProf: stderr:", process.stderr)

def filter_raw_file(raw_file: str, filtered_csv: str, columns_to_keep: list) -> None:
    """
    Parses the raw text file produced by AMD uProf.
    This file contains header information and a CSV portion.
    The function searches for the CSV header line (identified by the presence of "System instructions"
    and "IPC (Sys + User)") and then uses csv.DictReader to extract the data rows.
    It then writes only the specified columns to a new CSV file.
    """
    # Read all lines from the raw file.
    with open(raw_file, "r") as f:
        lines = f.readlines()

    # Look for the CSV header line (e.g., the line containing "System instructions (%)" and "IPC (Sys + User)")
    header_index = None
    for i, line in enumerate(lines):
        if "System instructions" in line and "IPC (Sys + User)" in line:
            header_index = i
            break

    if header_index is None:
        print("Error: CSV header not found in the raw file.")
        return

    # The CSV part starts at the header_index; assume subsequent lines are CSV formatted.
    csv_lines = lines[header_index:]
    csv_text = "".join(csv_lines)
    reader = csv.DictReader(csv_text.splitlines())
    
    # Determine which header fields to keep (only if they exist in the file)
    available_columns = reader.fieldnames
    if not available_columns:
        print("Error: No CSV header detected after the header marker.")
        return
    header = [col for col in columns_to_keep if col in available_columns]
    if not header:
        print("None of the desired columns were found in the CSV header.")
        return

    # Write the filtered data to the new CSV file.
    with open(filtered_csv, "w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for row in reader:
            filtered_row = {col: row[col] for col in header}
            writer.writerow(filtered_row)
    print(f"Filtered metrics have been saved to: {filtered_csv}")

def amduprof_monitoring(duration: int, sampling_interval: int, raw_file: str, filtered_csv: str) -> None:
    # Parameters for the AMD uProf command
    # duration = 20            # seconds
    # sampling_interval = 5000 # milliseconds (5 seconds per sample)
    # raw_csv = "/tmp/pcm4.csv"            # The output CSV from AMD uProf
    # filtered_csv = "/tmp/filtered_metrics.csv"  # Where the filtered data will be saved

    # Define the list of columns we want to keep
    # (these names should match exactly the CSV header produced by AMD uProf PCM)
    columns_to_keep = [
        "IPC (Sys + User)",
        "CPI (Sys + User)",
        "L2 Miss (pti)",
        "L2 Access (pti)",
        "L2 Hit (pti)",
        "Giga Instructions Per Sec"
    ]

    print("AMDuProf: Starting monitoring...")
    # Run AMD uProf PCM in a subprocess
    run_amduprof(duration, sampling_interval, raw_file)
    print("AMDuProf: Monitoring completed.")

    # Check if the raw CSV file was created and process it
    if os.path.exists(raw_file):
        filter_raw_file(raw_file, filtered_csv, columns_to_keep)
        print("AMDuProf: Filtered metrics have been written to:", filtered_csv)
    else:
        print("AMDuProf: Error: The output CSV file was not found:", raw_file)