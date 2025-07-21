# config.py
DURATION_MINUTES = 30
STEP_INTERVAL = 60  # seconds
BASE_RPS = 1000
TARGET_URL = "http://192.168.49.2:30080/"
LOG_DIR = "/home/george/logs/traffic_generator"

NGINX_METRICS_FIELDNAMES = [
    "Test_ID", "Minute", "Time", "RPS", "Throughput", "Avg_Latency",
    "P50_Latency", "P75_Latency", "P90_Latency", "P95_Latency",
    "P99_Latency", "Max_Latency", "Min_Latency", "Errors"
]

RPS_30MIN_GRADUAL_LOW = [
    800, 850, 900, 950, 1000,
    1050, 1100, 1150, 1200, 1250,
    1300, 1350, 1400, 1450, 1500,
    1550, 1600, 1650, 1700, 1750,
    1800, 1850, 1900, 1950, 2000,
    1950, 1900, 1850, 1800, 1750
]

RPS_30MIN_GRADUAL_WIDE = [
    500, 650, 800, 950, 1100,
    1300, 1500, 1700, 1900, 2100,
    2300, 2500, 2700, 2900, 3100,
    3300, 3500, 3700, 3900, 4000,
    3800, 3600, 3400, 3200, 3000,
    2800, 2600, 2400, 2200, 2000
]
