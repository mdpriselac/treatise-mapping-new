# Upload API. Build from the repo root:
#   docker buildx build --platform linux/amd64 -f upload/api/Dockerfile -t <image> .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TM_REFERENCE=/app/reference
WORKDIR /app
COPY upload/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY upload/api/app.py upload/job/profile_measures.py ./
COPY upload/job/reference/reference.json ./reference/
RUN useradd -m api && chown -R api /app
USER api
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
