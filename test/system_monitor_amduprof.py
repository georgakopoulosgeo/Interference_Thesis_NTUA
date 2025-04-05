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
        "sudo", "/opt/AMDuProf_5.0-1479/bin/AMDuProfPcm",  # Corrected path to the executable
        "-m", "ipc,l2",
        "-a",
        "-A", "system",
        "-d", str(duration),
        "-I", str(sampling_interval),
        "-o", output_csv
    ]
    # Execute the command and wait for it to complete.
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("AMDuProfPcm finished with return code:", process.returncode)
    if process.stdout:
        print("stdout:", process.stdout)
    if process.stderr:
        print("stderr:", process.stderr)

def filter_csv(input_csv: str, output_csv: str, columns_to_keep: list) -> None:
    """
    Reads the CSV produced by AMD uProf, filters to keep only the selected columns,
    and writes the result to a new CSV file.
    """
    with open(input_csv, "r") as infile:
        reader = csv.DictReader(infile)
        # Determine which columns from the header match our desired columns.
        header = [field for field in reader.fieldnames if field in columns_to_keep]
        if not header:
            print("AMDuProf: None of the desired columns were found in the CSV header.")
            return

        with open(output_csv, "w", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=header)
            writer.writeheader()
            for row in reader:
                # Write only the columns we need
                filtered_row = {col: row[col] for col in header}
                writer.writerow(filtered_row)

def amduprof_monitoring(duration: int, sampling_interval: int, raw_csv: str, filtered_csv: str) -> None:
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
    # Run AMD uProf PCM in a separate thread so that we can potentially manage concurrency
    thread = threading.Thread(target=run_amduprof, args=(duration, sampling_interval, raw_csv))
    thread.start()
    thread.join()  # Wait until AMD uProf finishes collecting data

    # Check if the raw CSV file was created and process it
    if os.path.exists(raw_csv):
        filter_csv(raw_csv, filtered_csv, columns_to_keep)
        print("AMDuProf: Filtered metrics have been written to:", filtered_csv)
    else:
        print("AMDuProf: Error: The output CSV file was not found:", raw_csv)