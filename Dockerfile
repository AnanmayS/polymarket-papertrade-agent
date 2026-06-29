FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gfortran libopenblas-dev liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install scipy + numpy as pre-built wheels FIRST so pip doesn't try to
# rebuild them from source as isolated build deps of scikit-learn.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir numpy==2.3.2 scipy && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
