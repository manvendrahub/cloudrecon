# Python FastAPI AI service — Optimized CPU build for c7i.flex.large
FROM python:3.11-slim

WORKDIR /app

# System libs needed by opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only PyTorch first, then other requirements to guarantee no CUDA bloat
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch torchvision \
 && pip install --no-cache-dir -r requirements.txt \
 && find /usr/local/lib/python3.11 -name "*.pyc" -delete \
 && find /usr/local/lib/python3.11 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

COPY app.py .

EXPOSE 8000

# 1 worker: optimal for 2 vCPU / 4 GB RAM on c7i.flex.large
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
