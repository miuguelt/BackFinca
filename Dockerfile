# Imagen base ligera
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala utilidades mínimas
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Copia dependencias
COPY requirements.txt .

# Instala dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente
COPY . .

# Puerto de aplicación
EXPOSE 8081

# Healthcheck hacia la ruta versionada
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8081/api/v1/health || exit 1

# Comando por defecto
CMD ["gunicorn", "--preload", "--workers", "2", "--threads", "2", "--timeout", "60", "--max-requests", "1000", "--max-requests-jitter", "100", "--bind", "0.0.0.0:8081", "wsgi:app"]
