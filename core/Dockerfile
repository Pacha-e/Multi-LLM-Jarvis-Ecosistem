FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg portaudio19-dev libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train classifier at build time
RUN python -c "from jarvis.agent.intent_classifier import train_classifier; train_classifier()" || true

EXPOSE 8000
CMD ["python", "run.py"]
