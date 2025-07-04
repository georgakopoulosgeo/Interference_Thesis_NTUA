# Stage 1: Builder stage
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Copy all necessary files
COPY . .

# Stage 2: Runtime stage
FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary files from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Ensure Python can find user-installed packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Make sure the pickle file is accessible
RUN chmod +r /app/models/slowdown_predictor.pkl

# Expose the port your app runs on
EXPOSE 5000

# Command to run your application
CMD ["python", "app.py"]