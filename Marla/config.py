COOLDOWN_PERIOD = 3  # minutes between major actions
SLO_THRESHOLD = 0.8  # Acceptable slowdown ratio
MAX_REPLICAS = 4
CHECK_INTERVAL_SEC = 60  # Check every minute

RPS_TO_REPLICAS = {
    1000: 2,
    1500: 3
}

CLUSTER_NODES = ['minikube', 'minikube-m02']

PREDICTOR_API_URL = "http://localhost:5000"  # URL of the slowdown predictor API

PLACEMENT_METRIC = "avg"  # Options: "avg", "max"


NAMESPACE = "default"
DEPLOYMENT_BASE = "my-nginx"
IMAGE = "nginx:1.21-alpine"
LABEL = {"app": "my-nginx"}
NODE_LABEL_KEY = "kubernetes.io/hostname"
