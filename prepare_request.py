import pandas as pd
import json

df = pd.read_csv("pcm_example.csv")

# Flatten to 1 vector (keep order consistent with training)
metrics = df.values.flatten().tolist()

payload = {
    "metrics": metrics,   # Adjust if preprocessing needed
    "replicas": 2,
    "rps": 2500
}

with open("test_payload.json", "w") as f:
    json.dump(payload, f, indent=2)

print("✅ JSON payload written to test_payload.json")
