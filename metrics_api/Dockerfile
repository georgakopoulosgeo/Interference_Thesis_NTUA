FROM python:3.10-slim

# Create working directory
WORKDIR /app

# Copy your Python code into the image
COPY app.py ./

# Install dependencies
RUN pip install flask

# Expose port for Flask
EXPOSE 8000

# Run the app
CMD ["python", "app.py"]
