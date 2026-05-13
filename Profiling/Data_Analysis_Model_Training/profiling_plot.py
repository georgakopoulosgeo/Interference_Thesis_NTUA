import pandas as pd

df = pd.read_pickle("complete_dataset_labeled.pkl")
df_cpu = df[df['Interference_Category'] == 'CPU'].copy()
df_baseline = df[df['Interference_Category'] == 'Baseline'].copy()

# 1. Get unique values for both RPS and Replicas
unique_rps = df_cpu['Given_RPS'].unique()
unique_replicas = df_cpu['Replicas'].unique()

# 2. Create "Isolation" rows for EVERY combination of RPS and Replicas
isolation_rows = []
for rps in unique_rps:
    for rep in unique_replicas:
        isolation_rows.append({
            'Scenario_Label': 'Isolation',
            'Given_RPS': rps,
            'Replicas': rep,
            'norm_perf': 1.0,
            'Interference_Category': 'CPU'
        })

df_isolation = pd.DataFrame(isolation_rows)

# 3. Combine
df_cpu_isolation = pd.concat([df_cpu, df_isolation], ignore_index=True)