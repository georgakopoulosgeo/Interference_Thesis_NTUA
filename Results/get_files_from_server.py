import subprocess
import os

remote_user = "george@147.102.13.77"

local_subfolders = [
    "traffic_generator_csvs",
    "naive_logs",
    "marla_logs"
]

remote_folders = [
    "/home/george/logs/traffic_generator",
    "/home/george/logs/naive",
    "/home/george/logs/marla"
]

remote_paths = [
    f"{remote_user}:{remote_folders[0]}/*.csv",
    f"{remote_user}:{remote_folders[1]}/*.jsonl",
    f"{remote_user}:{remote_folders[2]}/*.jsonl"
]

local_base = "/home/george/Workshop/Interference/Results"

for i in range(3):
    local_results_folder = os.path.join(local_base, local_subfolders[i])
    os.makedirs(local_results_folder, exist_ok=True)
    try:
        subprocess.run(["scp", remote_paths[i], local_results_folder], check=True)
        print(f"Files copied successfully to '{local_results_folder}'!")
    except subprocess.CalledProcessError as e:
        print(f"Error copying files for {local_subfolders[i]}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for {local_subfolders[i]}: {e}")
