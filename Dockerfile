FROM python:3.12-slim

WORKDIR /app

# deps de build (psycopg) + utilitários
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

# requirements (pode substituir por poetry/pdm depois)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
