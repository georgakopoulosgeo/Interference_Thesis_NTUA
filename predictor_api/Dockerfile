# Use the same Python version that was used to train the model
FROM python:3.10.12-slim

WORKDIR /app

# Install dependencies
RUN pip install pandas==2.0.3 scikit-learn==1.2.2 flask==2.3.2 requests==2.31.0 

# Copy the application code
COPY app.py .

# Create directory for model and copy the model file
RUN mkdir /model
COPY slowdown_predictor.pkl /model/

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]