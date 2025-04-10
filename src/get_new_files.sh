#!/bin/bash
# update_workspace.sh
# 1. Navigate to ~/Workspace/Interference, update the repository, and wait for 1 second.
# 2. Copy all files from ~/Workspace/Interference/test to ~/Workspace, replacing any existing files.

# Step 1: Update repository
cd ~/Workspace/Interference || { echo "Failed to change directory to ~/Workspace/Interference"; exit 1; }
git pull
sleep 1

# Step 2: Copy all files from ~/Workspace/Interference/test to ~/Workspace, replacing existing files
cp -rf ~/Workspace/Interference/test/* ~/Workspace/

echo "Workspace updated successfully."