FROM python:3.12-slim
WORKDIR /app

# System deps for LightGBM + psycopg2 (if you swap to Postgres)
RUN apt-get update && apt-get install -y libgomp1 gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Multiproc Prometheus support
RUN pip install --no-cache-dir "gunicorn==21.2.0"

COPY . .

# Prometheus multiprocess support — required when WEB_CONCURRENCY > 1
ENV PROMETHEUS_MULTIPROC_DIR=/var/c1b/prom_multiproc
ENV WEB_CONCURRENCY=4
RUN mkdir -p /var/c1b/prom_multiproc

EXPOSE 8001

# gunicorn + uvicorn workers; N workers share the multiproc dir.
# In dev / single-worker, unset PROMETHEUS_MULTIPROC_DIR and run plain uvicorn.
CMD ["sh", "-c", "rm -f $PROMETHEUS_MULTIPROC_DIR/*.db 2>/dev/null; \
     exec gunicorn server:app \
        --workers ${WEB_CONCURRENCY:-4} \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8001 \
        --timeout 60 \
        --graceful-timeout 30 \
        --access-logfile -"]
