DURATION_MINUTES = 30
STEP_INTERVAL = 60  # seconds
BASE_RPS = 1500
TARGET_URL = "http://nginx.default.svc.cluster.local"
LOG_DIR = "logs/"
# RPS levels for 30-minute predefined test (changes every 2 minutes)
PREDEFINED_RPS_30MIN = [
    1300, 1100, 1200, 1300, 1500,
    1600, 1700, 1800, 1900, 2000,
    2100, 2200, 2300, 2400, 2000
]

PREDEFINED_RPS_60MIN = [
    2500, 2800, 2400, 2500, 2700,
    2300, 2100, 2500, 2800, 3000,
    2900, 3100, 2900, 3000, 3200,
    3300, 3100, 2900, 2700, 2800,
    2600, 2500, 2300, 2100, 2200,
    2400, 2600, 2800, 3000, 3200
]