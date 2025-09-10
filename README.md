# KubeMarla — Interference-Aware Resource Management for Kubernetes

> Proof-of-concept scheduler that predicts slowdown from hardware interference and places workloads to minimize it.

---

## Abstract
*(Paste the official abstract from your thesis here. Keep it to ~150–200 words so the README stays developer-friendly.)*

---

## Table of Contents
- [Motivation & Problem Statement](#motivation--problem-statement)
- [Technologies / Tools Used](#technologies--tools-used)
- [Architecture / System Overview](#architecture--system-overview)
  - [KubeMarla Architecture](#kubemarla-architecture)
  - [Experiment Setup](#experiment-setup)
- [Installation & Setup](#installation--setup)
- [How to Run Experiments](#how-to-run-experiments)
- [Results (Optional)](#results-optional)
- [Repository Structure](#repository-structure)
- [Configuration](#configuration)
- [Reproducibility](#reproducibility)
- [Troubleshooting](#troubleshooting)
- [References](#references)
- [Contact / Acknowledgements](#contact--acknowledgements)
- [License](#license)
- [Citation](#citation)

---

## Motivation & Problem Statement
Running multiple containerized applications on shared nodes can trigger **resource interference** (e.g., L3 cache contention, memory bandwidth pressure), degrading SLOs even when CPU requests/limits look fine. Standard Kubernetes scheduling is largely interference-agnostic.  
**KubeMarla** introduces an interference-aware placement loop that:
1. **Collects** low-level hardware counters (via Intel PCM) and service KPIs (RPS/latency).
2. **Learns** a slowdown model (features: `mean`, `std`, `p95` of selected PCM groups).
3. **Predicts** interference under candidate placements.
4. **Places** pods to minimize predicted slowdown subject to capacity/SLO constraints.

---

## Technologies / Tools Used
- **Languages:** Python, (optionally Go for controller components)
- **Orchestration:** Kubernetes (tested with Minikube)
- **Metrics:** Intel PCM (DaemonSet), Prometheus (scrape & store)
- **Traffic / Workloads:** Nginx, Vegeta (or wrk)
- **ML Stack:** scikit-learn / XGBoost, pandas, NumPy
- **Runtime / Packaging:** Docker, Makefile, bash automation
- **(Optional)** Redis (shared RPS counter for multi-worker setups)

---

## Architecture / System Overview

### KubeMarla Architecture
*(Insert/commit your diagram as `docs/kubemarla-architecture.png` and reference it here.)*

**Components**
- **CRD & Controller:** Encodes interference-aware scheduling intent and reconciliation.
- **PCM Metrics Collector (DaemonSet):** Captures per-core / per-socket hardware counters.
- **Feature Builder:** Aggregates counters into `mean/std/p95` feature vectors per window.
- **Slowdown Predictor:** Trained model that estimates relative performance slowdown.
- **Placement Engine:** Scores nodes for each pending pod and selects minimal-slowdown placements.

### Experiment Setup
*(Insert/commit `docs/experiment-setup.png`.)*

- **Cluster:** Minikube with 1 control plane + 1–2 worker nodes (CPU pinning where possible).
- **Target App:** Nginx behind a Service; replicas scaled during tests.
- **Load Gen:** Vegeta or wrk driving steady or bursty RPS.
- **Interference Pods:** CPU, L3, MemBW, Mixed (iBench or custom stressors).
- **Telemetry:** Prometheus scrapes PCM exporter + app metrics; logs stored for ML.

---

## Installation & Setup

The experiments were conducted on an Intel NUC with:
- 8 CPU cores
- 8 GB RAM

KubeMarla and its supporting services (PCM collector, REST APIs, controller) were pinned to cores 6–7.

Steps

Step 1 — Create the Minikube Cluster
Start a 2-node Minikube cluster with explicit CPU and memory allocations:

minikube start \
  --driver=docker \
  --cpus=3 \
  --memory=3072 \
  --container-runtime=containerd \
  --nodes=2 \
  --extra-config=kube-proxy.mode=ipvs

Step 2 — Configure CPU Pinning
Manually assign dedicated CPU cores to each node container:

docker update minikube --cpus=3 --cpuset-cpus="0-2"
docker update minikube-m02 --cpus=3 --cpuset-cpus="3-5"

Step 3 — Verify cgroup Configuration
Check inside each node (via SSH) that the assigned CPU set is correct:

minikube ssh -n minikube "cat /sys/fs/cgroup/cpuset.cpus"
minikube ssh -n minikube-m02 "cat /sys/fs/cgroup/cpuset.cpus"

Expected output:
- minikube → 0-2
- minikube-m02 → 3-5

Step 4 — Run KubeMarla Components

(a) Run PCM Monitoring (from Interference/metrics_collector):
./pcm_monitoring

(b) Start Metrics REST API (from same directory):
python app.py

(c) Start Predictor REST API (from Interference/predictor_api):
python app.py
(Ensure the correct Python environment is activated.)

(d) Start KubeMarla controller with log file name:
python controller.py <name_of_logs>

At this point, KubeMarla is active and ready to schedule workloads under the interference-aware placement policy.



### How to Run Experiments

### Results (Optional)

### Repository Structure
Auto Thelei ftiaksimo

### Configuration
mpa


### Reproducibility
mpa

### Troubleshooting

### References

### Contact / Acknowledgements

### License

### Citation
