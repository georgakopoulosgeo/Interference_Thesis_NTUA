import joblib

model = joblib.load("models/slowdown_predictor.pkl")  # Old model
joblib.dump(model, "models/slowdown_predictor_clean.pkl")  # Clean save