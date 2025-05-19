FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for PCM/sklearn
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for models
RUN mkdir -p /app/models

# Copy your trained model and feature columns
COPY slowdown_predictor_model.pkl /app/models/
COPY feature_columns.pkl /app/models/

ENV MODEL_PATH=/app/models/slowdown_predictor_model.pkl
ENV FEATURE_COLUMNS_PATH=/app/models/feature_columns.pkl

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]