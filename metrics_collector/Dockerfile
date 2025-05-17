FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for PCM
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    libncurses5-dev && \
    rm -rf /var/lib/apt/lists/*

# Install PCM (replace with your actual PCM installation)
RUN wget https://github.com/opcm/pcm/archive/refs/tags/202301.zip && \
    unzip 202301.zip && \
    cd pcm-202301 && \
    make && \
    cp pcm*.x /usr/local/bin/ && \
    cd .. && \
    rm -rf 202301.zip pcm-202301

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]