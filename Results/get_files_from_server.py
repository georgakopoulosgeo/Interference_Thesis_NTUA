import subprocess
import os

remote_user = "george@147.102.13.77"

# For traffic_generator_csvs
#local_subfolder = "traffic_generator_csvs"  # or any name you prefer
#remote_folder = "/home/george/logs/traffic_generator"
#remote_path = f"{remote_user}:{remote_folder}/*.csv"

# For naive_logs
local_subfolder = "naive_logs" 
remote_folder = "/home/george/logs/naive"
remote_path = f"{remote_user}:{remote_folder}/*.jsonl"

# For marla_logs
local_subfolder = "marla_logs"
remote_folder = "/home/george/logs/marla"
remote_path = f"{remote_user}:{remote_folder}/*.jsonl"

# Full local path to store files
local_base = "/home/george/Workshop/Interference/Results"
local_results_folder = os.path.join(local_base, local_subfolder)

# Ensure the local folder exists
os.makedirs(local_results_folder, exist_ok=True)

# SCP the CSVs from server
try:
    subprocess.run(["scp", remote_path, local_results_folder], check=True)
    print(f"CSV files copied successfully to '{local_results_folder}'!")
except subprocess.CalledProcessError as e:
    print(f"Error copying files: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
