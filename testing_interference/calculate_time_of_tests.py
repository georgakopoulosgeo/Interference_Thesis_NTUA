import math

DURATION = "3m"  # Test duration per run
REPLICAS_TO_TEST = [1, 2,3,4]  # Number of replicas to test
RPS_STEPS = [500]  # RPS steps to test
INTERFERENCE_SCENARIOS = range(1, 16)

# PCM monitoring configuration
STABILATION_TIME_AFTER_DELETION = 10       # Time to wait for system stabilization after deletion of workloads
STABILATION_TIME_AFTER_DEPLOYMENT = 10      # Time to wait for system stabilization after deployment of workloads
STABILATION_TIME_AFTER_INTERFERENCE = 10    # Time to wait for system stabilization of interference pods
SLEEP_BETWEEN_TESTS = 30                  # Sleep time between tests to allow system to stabilize

STABILATION_TIME_MIX_SCENARIOS = 12         # Longer stabilization for mixed scenarios
STABILATION_TIME_AFTER_WARMUP = 10          # Time to wait for system stabilization after warmup / IGNORE
STABILATION_TIME_NEW_REPLICAS = 22          # Time to wait before tests for new replicas

def calculate_time_of_tests():
    total_duration = 0
    for replicas in REPLICAS_TO_TEST:
        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                # Each test runs for DURATION + stabilization times
                total_duration += STABILATION_TIME_AFTER_DEPLOYMENT + STABILATION_TIME_AFTER_INTERFERENCE + int(DURATION[:-1])*60 + SLEEP_BETWEEN_TESTS
    print(f"Total execution duration: {total_duration} seconds", flush=True)
    print(f"Total execution duration: {total_duration / 60} minutes", flush=True)
    print(f"Total execution duration: {total_duration / 3600} hours", flush=True)

if __name__ == "__main__":
    calculate_time_of_tests()