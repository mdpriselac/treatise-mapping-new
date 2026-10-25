# Upload parse job. Build from the repo root:
#   docker buildx build --platform linux/amd64 -f upload/job/Dockerfile -t <image> .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    TM_REFERENCE=/app/reference TM_TREATISE=/app/reference/treatise.txt \
    HF_HOME=/app/.cache/hf XDG_CACHE_HOME=/app/.cache HF_HUB_OFFLINE=0
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY upload/job/requirements.txt .
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt
COPY pipeline/detect.py pipeline/quote_check.py pipeline/score.py pipeline/adjudicate.py pipeline/paths.py ./
COPY upload/job/uploadprof.py upload/job/profile_measures.py upload/job/main.py upload/job/warmup.py ./
COPY upload/job/reference ./reference
RUN python warmup.py
# From here on models load from the image cache only
ENV HF_HUB_OFFLINE=1
RUN useradd -m job && chown -R job /app
USER job
CMD ["python", "main.py"]
