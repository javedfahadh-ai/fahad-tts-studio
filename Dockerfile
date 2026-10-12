FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TTS_VOICES_DIR=/data/voices \
    TTS_OUTPUT_DIR=/data/output \
    TTS_DB_PATH=/data/tts_history.db

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
        espeak-ng-data \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/tts
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/
COPY scripts/ ./scripts/

RUN mkdir -p /data/voices /data/output

# Render provides $PORT dynamically — listen on it (default 10000 locally)
EXPOSE 10000
HEALTHCHECK --interval=60s --timeout=10s CMD curl -f http://localhost:${PORT:-10000}/api/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
