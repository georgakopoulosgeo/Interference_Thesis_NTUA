FROM python:3.10.12-slim

WORKDIR /app

# Install specific versions to avoid compatibility issues
RUN pip install --no-cache-dir \
    numpy==1.23.5 \
    pandas==1.5.3 \
    scikit-learn==1.2.2 \
    flask==2.2.3 \
    requests==2.28.2

COPY app.py .
RUN mkdir /model
COPY slowdown_predictor.pkl /model/

EXPOSE 5000
CMD ["python", "app.py"]