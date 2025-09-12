FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Expose port for API server
EXPOSE 8000

# Default to API server mode, but can be overridden
CMD ["python", "benson_system.py", "--mode", "api-server", "--port", "8000"]
