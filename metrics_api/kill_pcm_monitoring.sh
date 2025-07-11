#!/bin/bash

# Find the PID of the running ./pcm_monitoring.sh script (but not grep)
PID=$(ps aux | grep '[.]\/pcm_monitoring.sh' | grep -v grep | awk 'NR==1 {print $2}')

if [ -z "$PID" ]; then
  echo "No running pcm_monitoring.sh process found."
  exit 1
fi

echo "Found pcm_monitoring.sh running with PID: $PID"
echo "Stopping pcm_monitoring.sh..."
sudo kill "$PID"