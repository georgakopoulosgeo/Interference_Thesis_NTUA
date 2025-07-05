# Use the same Python version that was used to train the model
FROM python:3.10.12-slim

WORKDIR /app

# Install dependencies
RUN pip install flask scikit-learn pandas numpy requests jsonify

# Copy the application code
COPY app.py .

# Create directory for model and copy the model file
RUN mkdir /model
COPY slowdown_predictor.pkl /model/

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]