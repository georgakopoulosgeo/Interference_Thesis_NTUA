# Use official lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code and model
COPY app.py .
COPY models/ ./models/

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
