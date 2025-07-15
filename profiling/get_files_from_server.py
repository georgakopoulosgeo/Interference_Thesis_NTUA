import subprocess
import os

# User-defined variables
name_of_local_folder = "profiling/Rear_Window_V01"
name_of_server_folder = "Rear_Window_V01"

# Remote and local paths
remote_user = "george@147.102.13.77"
remote_path = f"{remote_user}:/home/george/Workspace/{name_of_server_folder}/*"
local_results_folder = os.path.join(os.getcwd(), name_of_local_folder)

# Create local folder if it doesn't exist
os.makedirs(local_results_folder, exist_ok=True)

# Use subprocess to securely copy all files from remote
try:
    subprocess.run(["scp", remote_path, local_results_folder], check=True)
    print(f"Files copied successfully to '{local_results_folder}'!")
except subprocess.CalledProcessError as e:
    print(f"Error copying files: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")