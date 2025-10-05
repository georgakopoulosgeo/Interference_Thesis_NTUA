# Interference-Aware Dynamic Replica Management for LC-Workloads in Kubernetes

> In this Proof-of-concept thesis we propose a closed-loop runtime controller that uses a Machine Learning Model to predict the Normalized Perfomance of LC-workloads from hardware Interference and distributes them to nodes, in order to maximaze the performance.

---

## 0. Abstract
The rapid growth of cloud computing applications by both businesses and individual users has led to a massive increase in microservices that are based on containerized architectures. 
Many of these microservices consist of latency-critical (LC) applications, such as Web Servers and online transaction systems, where even small delays can significantly impact user experience.
To manage the enormous number of containers, Data Centers rely on orchestrators, such as Kubernetes, and techniques like co-location and multi-tenancy. 
These practices result in resource contention over shared hardware resources (e.g. CPU, cache, memory bandwidth), severely degrading the quality of a service in comparison to the application running on isolation, a phenomenon called Performance Interference. However, default schedulers make placement decisions based only on static CPU and memory utilization, without being aware of the impact of interference and the dynamic workload of these applications. 

In this thesis, we propose an architecture that dynamically redistributes replicas of existing workloads across cluster nodes, while taking into consideration the impact of interference.
We first show the effect of applying stress on different shared resources and its impact on the performance of a latency-critical workload. As a representative case study, we focus on the Nginx Web Server, a widely used front-end service in microservice architectures. 
Using hardware performance counters collected with Intel PCM, we train an XGBoost regression model with cross-validated mean absolute error CV-MAE=0.117, capable of predicting performance slowdowns under various traffic and interference conditions. The model also achieves R^2 = 0.90, indicating its explanatory strength.
Using this model, we design an interference-aware closed-loop control architecture which adaptively selects replica placement plans across nodes of a cluster in real time. 
Experimental evaluation in multiple dynamic interference scenarios showed that our implementation, called Marla, outperforms the default Kubernetes scheduler, achieving an average 17.8% reduction in p_99 latency in realistic mixed interference scenarios, with reductions going up to 34.9% depending on the type of interference, while at the same time improving overall resource utilization. These results confirm that interference-aware controllers can meet QoS requirements without relying on costly over-provisioning.


## Table of Contents
- [0. Abstract](#0-abstract)
- [1. Background & Motivation](#1-background--motivation)
- [2. System Architecture](#2-system-architecture)
- [3. Experimental Setup](#3-experimental-setup)
  - [3.1 Hardware and Cluster Configuration](#31-hardware-and-cluster-configuration)
  - [3.2 Workload and Interference Generators](#32-workload-and-interference-generators)
  - [3.3 Monitoring and Telemetry Pipeline](#33-monitoring-and-telemetry-pipeline)
- [4. Phase A Experiments - Interfernce understanding and Dataset Generation](#4-phase-a-experiments---interfernce-understanding-and-dataset-generation)
  - [4.1 Interference Scenarios](#41-experimental-matrix)
  - [4.2 Traffic Profiles](#42-traffic-profiles)
  - [4.3 Data Collection Process (PCM + Vegeta)](#43-data-collection-process-pcm--vegeta)
- [5. Model Training](#5-model-training)
  - [5.1 Objective](#51-objective)
  - [5.2 Statistical Analysis & Feature Engineering](#52-statistical-analysis--feature-engineering)
  - [5.3 Model Configuration, Training and Validation](#53-model-configuration-training-and-validation)
  - [5.4 Output](#54-output)
- [6. Phase B Experiments - Marla Evaluation](#6-phase-b-experiments---marla-evaluation)
  - [6.1 Objective](#61-objective)
  - [6.2 Runtime Operation](#62-runtime-operation)
  - [6.3 Experimental Design](#63-experimental-design)
  - [6.4 Metrics and Baselines](#64-metrics-and-baselines)
- [7. Repository Structure](#7-repository-structure)
- [8. Installation & Usage](#8-installation--usage)
- [9. Results and Key Findings](#9-results-and-key-findings)
- [10. Acknowledgments](#10-acknowledgments)

---

## 1. Background & Motivation
Running multiple containerized applications on shared nodes can trigger **resource interference** (e.g., L3 cache contention, memory bandwidth pressure), degrading SLOs even when CPU requests/limits look fine. Standard Kubernetes scheduling is largely interference-agnostic.  
**Marla** introduces an interference-aware placement loop that:
1. **Collects** low-level hardware counters (via Intel PCM) and service KPIs (RPS/latency).
2. **Learns** a slowdown model (features: `mean`, `std`, `p95` of selected PCM groups).
3. **Predicts** interference under candidate placements.
4. **Places** pods to minimize predicted slowdown subject to capacity/SLO constraints.

---

## 2. System Architecture
<p align="center">
  <img src="docs/Marla_architecture.png" alt="MARLA Architecture" width="700">
</p>

The architecture of MARLA follows a **modular, closed-loop control design** integrated into a two-node Kubernetes cluster.  
It continuously collects hardware-level telemetry, predicts workload slowdown under different placements, forecasts future load, and issues replica reallocation commands to the cluster.

### 2.1 Components
- **Metrics Collector:**  
  A per-node daemon built around Intel’s *Performance Counter Monitor (PCM)*.  
  It periodically samples hardware counters (CPU utilization, cache misses, memory bandwidth, etc.) and exposes the aggregated statistics (`mean`, `std`, `p95`) via a REST endpoint (`/metrics/csv`).

- **Slowdown Predictor:**  
  A Python REST API that loads a pretrained **XGBoost regression model**.  
  Given the current PCM metrics, replica count, and predicted RPS, it outputs a *normalized performance score* for each node—essentially estimating how close each node is to its baseline performance.

- **ARIMA Forecaster:**  
  A time-series model that predicts the next-minute **incoming request rate (RPS)** based on the recent traffic window.  
  It allows MARLA to act proactively, not just reactively, to load changes.

- **MARLA Controller:**  
  The core decision module running as a standalone service or Deployment.  
  Every minute, it:
  1. Fetches the latest metrics and RPS prediction.  
  2. Queries the slowdown predictor for all feasible replica allocations.  
  3. Computes the aggregated slowdown for each plan and selects the optimal one.  
  4. Scales Nginx replicas across nodes through the Kubernetes API.  
  Built-in cooldown and thresholding prevent oscillatory scaling.

### 2.2 Data Flow Summary
1. **PCM metrics** → Metrics Collector → REST API  
2. **Controller** fetches metrics + **ARIMA** forecast → builds feature vector  
3. **Predictor API** returns per-node slowdown scores  
4. **Controller** computes best replica plan → applies scaling through Kubernete

---

## 3. Experimental Setup

### 3.1 Hardware and Cluster Configuration
Experiments were conducted on an **Intel NUC** with:
- 8 CPU cores and 8 GB RAM  
- **2-node Minikube cluster**, using CPU pinning via `cpuset`  
  - Node 1 → cores 0–2  
  - Node 2 → cores 3–5  
- Each node assigned 3 GB RAM and 3 vCPUs  

This setup semi-isolates hardware interference between nodes while preserving realistic resource contention within each node.

### 3.2 Workload and Traffic Generation
The target workload is an **Nginx Web Server**, representing a latency-critical microservice.  
Traffic is generated using **Vegeta**, with RPS values ranging from **500 to 4000** to emulate light to heavy loads.  
Each test lasts **30 minutes**, with stepwise changes in traffic every minute.

### 3.3 Interference Injection
Hardware interference is injected using **iBench** pods deployed in both nodes.  
Four stress types are used:
- **CPU interference**  
- **L3 cache contention**  
- **Memory bandwidth saturation**  
- **Mixed interference (CPU + L3 + MemBw)**  



---
## 4. Phase A Experiments - Interfernce understanding and Dataset Generation
<p align="center">
  <img src="docs/PhaseAExperiment_arch_v1.png" alt="Phase A Experiment Architecture" width="700">
</p>
### 4.1 Objective
The first phase focuses on building a comprehensive dataset that captures how **hardware-level interference** and **traffic load** affect the performance of a latency-critical workload.  
This dataset serves as the foundation for training the ML slowdown predictor later used by MARLA.

### 4.1 Experimental Matrix
To capture the full spectrum of performance interference, each scenario was defined by **the number and type of iBench pods** deployed on the two worker nodes.  
These pods generate controlled stress on selected hardware subsystems (CPU, cache, or memory), allowing reproducible interference conditions.

In total, **21 interference scenarios** were tested, including:
- **Baseline (no interference)**: no iBench pods running.  
- **4 × CPU-intensive**: varying number of CPU-stress pods per node.  
- **4 × L3 cache–intensive**: iBench pods stressing the last-level cache.  
- **4 × Memory-bandwidth–intensive**: pods saturating the memory subsystem.  
- **8 × Mixed**: combined CPU + L3 + MemBw interference through multiple ibench-pod types.

Additionally, we tested:
- **8 traffic levels:** 500 → 4000 RPS (increments of 500).  
- **4 replica configurations:** 1, 2, 3, and 4 Nginx replicas.

Each unique combination of interference type, traffic load, and replica count produced one data sample consisting of the collected hardware counters, the replica configuration, the applied RPS, and the corresponding measured **p99 latency**.


### 4.2 Data Collection Procedure
1. Deploy the selected interference pods on both nodes.  
2. Apply the chosen Nginx replica configuration.  
3. Generate steady traffic with Vegeta for 60 seconds.  
4. Record:
   - PCM metrics (mean, std, p95 of selected counters)  
   - Request throughput and p99 latency from Nginx logs  
5. Append all results to a central CSV dataset.

### 4.3 Dataset Summary
The final dataset contains **1898 samples × 65 features**, combining hardware-level metrics with application-level indicators.  
Features include:
- CPU utilization, cache miss ratios, memory bandwidth, core cycles  
- Statistical aggregates (mean / std / p95)  
- Replica count and input RPS  

The **target variable** is the *normalized performance slowdown*, defined as the ratio between the measured and the baseline p99 latency:
$$S_{norm} = \frac{p99_{measured}}{p99_{baseline}}$$


where:
- \( p99_{measured} \) is the observed 99th-percentile latency under the current interference and load conditions, and  
- \( p99_{baseline} \) is the latency of the same workload running in isolation (no interference).

A value of \( S_{norm} = 1 \) indicates baseline performance, while higher values represent degraded performance due to interference.


---

## 5. Regression Model Training

### 5.1 Objective
The goal of this phase is to train a regression model capable of predicting the **normalized performance slowdown** of a workload given current hardware metrics, replica count, and incoming traffic rate (RPS).  
The trained model is later embedded into the MARLA slowdown predictor API.

### 5.2 Statistical Analysis & Feature Engineering
Before model training, we conducted statistical preprocessing on the raw PCM dataset to remove redundant or highly correlated metrics and extract meaningful performance indicators.

For each metric group (CPU, cache, memory, bandwidth), three statistical features were computed:
- Mean value (`mean`)
- Standard deviation (`std`)
- 95th percentile (`p95`)

These aggregations capture both the central tendency and temporal variability of hardware behavior during each test interval.

After this analysis, the final dataset consisted of **1,898 samples × 27 features**, integrating:
- Aggregated PCM metrics (mean / std / p95)
- Active replica count
- Incoming RPS
- Label: normalized performance slowdown

This reduced representation preserved the core variability of the workload while improving model stability and training efficiency.

### 5.3 Model Configuration, Training and Validation
Model used:
```python
XGBoost: xgb.XGBRegressor(objective='reg:squarederror', random_state=42)
```

The dataset was split into **80 % training** and **20 % test** subsets.  
Model validation was performed using 5-fold cross-validation to ensure robustness across interference types and traffic levels.

Performance metrics:
- **Coefficient of determination:** \( R^2 = 0.90 \)  
- **Cross-validated Mean Absolute Error:** \( \text{CV-MAE} = 0.117 \)
- **Mean Absolute Error:** \( MAE: 0.0742 \)

### 5.4 Output
The trained model (`xgb_model.json`) serves as the core of the **Slowdown Predictor API**, which receives real-time PCM metrics and returns predicted normalized performance for each node.  
This allows MARLA to evaluate multiple replica placement options before applying any changes.


---
## 6. Phase B Experiments - Marla Evaluation
<p align="center">
  <img src="docs/PhaseBExperiment_v3.png" alt="Phase B Experiment Architecture" width="700">
</p>

### 6.1 Objective
The second experimental phase evaluates the runtime behavior of **MARLA**, the interference-aware controller that integrates the trained slowdown model and the ARIMA traffic predictor into a closed-loop decision process.  
The goal is to assess whether MARLA can dynamically adapt replica placement to maintain low latency under changing traffic and interference conditions.

### 6.2 Runtime Operation
MARLA runs as an active controller inside the Kubernetes cluster and executes every **60 seconds**.  
During each control cycle, it performs the following steps:

1. **Forecast traffic:**  
   Uses an **ARIMA (AutoRegressive Integrated Moving Average)** model to predict the next-minute request rate (RPS) based on the last 5–10 historical values.

2. **Collect system state:**  
   Fetches the latest PCM metrics from each node via the **Metrics Collector API**, along with the current replica distribution of Nginx pods.

3. **Query slowdown predictor:**  
   Sends all feasible combinations of replica allocations to the **ML Slowdown Predictor API**, which returns a predicted normalized performance slowdown for each node.

4. **Compute aggregated slowdown:**  
   For every candidate placement, MARLA evaluates the overall expected performance using the following equation:

   $$AggSlowdown = \frac{R_1 \cdot S_1 + R_2 \cdot S_2}{R_1 + R_2}$$

   where \( R_i \) is the number of replicas and \( S_i \) the predicted normalized slowdown on node \( i \).

5. **Select optimal placement:**  
   The configuration with the highest aggregated normalized slowdown (closest to 1) is selected as the target plan.

6. **Apply scaling actions:**  
   If the new plan differs from the current one and exceeds the predefined performance improvement threshold, MARLA updates the replica distribution through the Kubernetes API.

To avoid unnecessary oscillations, the controller includes:
- **Cooldown logic**, preventing consecutive reallocations within short time windows.  
- **Thresholding**, ensuring only meaningful performance improvements trigger migration.

### 6.3 Experimental Design
A **30-minute dynamic test** was performed, consisting of both:
- Gradual **traffic variations** (±200–500 RPS per minute), generated with Vegeta.  
- Periodic **interference injections**, where iBench pods were deployed, scaled, and removed to emulate changing contention levels across CPU, L3 cache, and memory bandwidth.

Throughout the test, MARLA continuously monitored and adapted the placement of Nginx replicas between the two Minikube nodes.

### 6.4 Metrics and Baselines
The evaluation focused on:
- **Primary metric:** SLO violation rate (percentage of requests exceeding target latency).  
- **Secondary metric:** Average **p99 latency** of Nginx responses.  

MARLA’s performance was compared against:
- The **default Kubernetes scheduler** (static placement).  
- A **static Horizontal Pod Autoscaler (HPA)** configuration, reacting only to CPU utilization.


---

## 7. Repository Structure
```bash
.
├── marla_controller/
│   ├── controller.py
│   ├── predictor_api/
│   ├── metrics_collector/
│   ├── arima_forecaster/
│   └── ...
├── experiments/
├── data/
├── notebooks/
├── docs/
└── README.md
```

---

## 8. Installation & Usage

### 8.1 Prerequisites
Before running the experiments, ensure the following dependencies are installed:
- **Python 3.10+**
- **Docker** and **Minikube**
- **Intel PCM** (Performance Counter Monitor)
- **Vegeta** (HTTP traffic generator)

The setup was tested on an **Intel NUC (8 cores / 8 GB RAM)**.

---

### 8.2 Cluster Setup

#### Step 1 — Create a Two-Node Minikube Cluster
Start Minikube with explicit CPU and memory allocations:

```bash
minikube start \
  --driver=docker \
  --cpus=3 \
  --memory=3072 \
  --container-runtime=containerd \
  --nodes=2 \
  --extra-config=kube-proxy.mode=ipvs
```

#### Step 2 — Configure CPU Pinning
Manually assign dedicated CPU cores to each node container to isolate interference:

```bash
docker update minikube --cpuset-cpus="0-2"
docker update minikube-m02 --cpuset-cpus="3-5"
```

#### Step 3 — Verify cgroup Configuration
Check inside each node that the CPU sets are applied correctly:

```bash
minikube ssh -n minikube "cat /sys/fs/cgroup/cpuset.cpus"
minikube ssh -n minikube-m02 "cat /sys/fs/cgroup/cpuset.cpus"
```

Expected output:
```
minikube → 0-2
minikube-m02 → 3-5
```

---

### 8.3 Component Deployment

#### (a) Start PCM Monitoring
From `metrics_collector/`:
```bash
./pcm_monitoring
```

#### (b) Run Metrics REST API
```bash
python app.py
```

#### (c) Launch Slowdown Predictor API
From `predictor_api/`:
```bash
python app.py
```

#### (d) Start ARIMA Forecaster (optional)
```bash
python arima_forecaster/app.py
```

#### (e) Run MARLA Controller
From `marla_controller/`:
```bash
python controller.py <log_name>
```

At this point, MARLA is active and ready to manage replicas under the interference-aware control policy.

---

### 8.4 Running Experiments

#### Phase A — Dataset Generation
Execute the experiment coordinator to automatically run all interference, traffic, and replica combinations:
```bash
cd testing
python coordinator_testing.py
```

#### Phase B — Dynamic Evaluation
- **Naive Baseline:**  
  Deploy standard (interference-agnostic) Nginx replicas and run:
  ```bash
  ./naive_experiment.sh
  ```
- **MARLA Controller:**  
  Deploy MARLA components, then execute:
  ```bash
  ./marla_experiment.sh
  ```

All experiment logs and PCM metrics are stored locally for subsequent analysis and plotting.


---

## 9. Results & Key Findings
<p align="center">
  <img src="docs/results_table.png" alt="Results of Experimental Evaluation" width="700">
</p>

Across multiple interference scenarios, MARLA consistently achieved:
- **17.8–34.9 % reduction in average p99 latency**, depending on the interference type.  
- Significant decrease in SLO violation rate, especially under mixed CPU–L3–MemBw contention.  
- Stable behavior under dynamic conditions, without oscillations or excessive scaling events.

These results confirm that integrating ML-based slowdown prediction and short-term traffic forecasting into a closed-loop control mechanism enables **adaptive, interference-aware resource management** that outperforms conventional Kubernetes scheduling policies. 


---

## 10. Acknowledgments
This work was conducted at the **NETMODE Lab, National Technical University of Athens (NTUA)**.  
Supervisors: Prof. Simeon Papavassiliou, Dr. Dimitris Spatharakis.  

