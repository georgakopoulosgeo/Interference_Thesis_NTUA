# metrics_collector/Dockerfile

FROM python:3.9-slim

# Install build tools and dependencies for PCM
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git \
      cmake \
      build-essential \
      python3-dev \
      libpci-dev && \
    rm -rf /var/lib/apt/lists/*

# Clone and build Intel PCM
RUN git clone --recursive https://github.com/intel/pcm /opt/pcm && \
    mkdir /opt/pcm/build && \
    cd /opt/pcm/build && \
    cmake .. && \
    cmake --build . --parallel && \
    # Symlink pcm binary into PATH
    ln -s /opt/pcm/build/pcm.x /usr/local/bin/pcm

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy collector and API code
COPY collector/ collector/
COPY service/ service/

EXPOSE 8000

# Launch the FastAPI server
CMD ["uvicorn", "service.api:app", "--host", "0.0.0.0", "--port", "8000"]
