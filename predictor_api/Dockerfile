FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy models and app code
COPY models/ ./models/
COPY app.py .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]