FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify model can be loaded during build
COPY models/ ./models/
RUN python -c "import joblib; joblib.load('./models/slowdown_predictor.pkl')" || echo "Model verification failed"

COPY app.py .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]