#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>
#include <unistd.h>

#define NS_PER_S (1000000000L)

// Get current time in nanoseconds
uint64_t getNs() {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec * NS_PER_S + ts.tv_nsec;
}

// Busy-wait for the specified number of nanoseconds
void busyWait(uint64_t durationNs) {
    uint64_t start = getNs();
    while (getNs() - start < durationNs);
}

// Sleep for the specified number of nanoseconds using nanosleep
void sleepNs(uint64_t durationNs) {
    struct timespec req, rem;
    req.tv_sec = durationNs / NS_PER_S;
    req.tv_nsec = durationNs % NS_PER_S;
    nanosleep(&req, &rem);
}

int main(int argc, const char** argv) {
    // Usage: "./cpu <duration in sec> [load percentage (0-100)]"
    if (argc < 2) {
        printf("Usage: ./cpu <duration in sec> [load percentage 0-100]\n");
        exit(0);
    }
    
    int totalDurationSec = atoi(argv[1]);
    double loadPercentage = 100.0;  // Default 100% load
    if (argc >= 3) {
        loadPercentage = atof(argv[2]);
        if (loadPercentage < 0.0) loadPercentage = 0.0;
        if (loadPercentage > 100.0) loadPercentage = 100.0;
    }
    
    uint32_t maxThreads = omp_get_num_procs();
    printf("Running for %d sec at %.1f%% load using %d threads\n", totalDurationSec, loadPercentage, maxThreads);
    
    // Define a cycle period (e.g., 10ms)
    uint64_t cycleNs = 10 * 1000000L; // 10ms in nanoseconds
    // Calculate busy and idle durations for the cycle
    uint64_t busyTime = (uint64_t)(cycleNs * (loadPercentage / 100.0));
    uint64_t idleTime = cycleNs - busyTime;
    
    uint64_t endTime = getNs() + totalDurationSec * NS_PER_S;
    
    #pragma omp parallel
    {
        while (getNs() < endTime) {
            busyWait(busyTime);
            sleepNs(idleTime);
        }
    }
    
    return 0;
}

