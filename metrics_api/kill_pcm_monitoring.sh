#!/bin/bash

# Kill the PCM process and the rotation loop
sudo pkill -f "/home/george/Workspace/pcm/build/bin/pcm"
sudo pkill -f "tail -n 30 raw_metrics.csv"
