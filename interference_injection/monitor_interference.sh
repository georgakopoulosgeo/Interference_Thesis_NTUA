Nice.
Now give me a bash script to run alongside with each of these test to monitor the level of interference by studying the pressure on hardware counters:

The tool I use is the pcm.
In previous tests I used this python code:
    # Go to the directory where the PCM tool is located.
    pcm_dir = "/home/george/Workspace/pcm/build/bin"
    os.chdir(pcm_dir)
    cmd = ["sudo", "./pcm", str(interval), "-csv=" + output_csv]