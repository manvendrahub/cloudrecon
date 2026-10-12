# Python FastAPI AI service
FROM python:3.11-slim

WORKDIR /app

# System libs needed by opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Upgrade pip and install deps; simple-lama-inpainting may download weights on first run
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

# Use 2 workers; for heavy images keep 1 to avoid OOM on small EC2 instances
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
