import subprocess
import os

# Local subfolder for storing results
local_subfolder = "traffic_generator_csvs"  # or any name you prefer

# Define server details and paths
remote_user = "george@147.102.13.77"
remote_folder = "/home/george/logs/traffic_generator"
remote_path = f"{remote_user}:{remote_folder}/*.csv"

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
