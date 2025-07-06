# Use a slim Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source files
COPY app.py pcm_reader.py ./

# Expose the port used by Flask
EXPOSE 8000

# Command to run the Flask app
CMD ["python", "app.py"]
