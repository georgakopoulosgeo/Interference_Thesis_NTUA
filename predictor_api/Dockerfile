# Use the same Python version that was used to train the model
FROM python:3.10.12-slim

WORKDIR /app

# Install dependencies
RUN pip install flask scikit-learn pandas numpy requests jsonify joblib

# Copy the application code
COPY app.py .

# Create directory for model and copy the model file
RUN mkdir /model
COPY slowdown_predictor.pkl /model/

# Expose the port the app runs on
EXPOSE 5000

# Add PYTHONUNBUFFERED and FLASK_DEBUG environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=1

CMD ["python", "-u", "app.py"] 