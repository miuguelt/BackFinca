###############
# Dockerfile optimizado para Flask + Gunicorn
# - Instala wget para que el HEALTHCHECK funcione
# - Usa build deps temporales y las elimina
# - Usa usuario no root
# - Compatible con Alpine Linux
###############

FROM python:3.12-alpine AS app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081

WORKDIR /app

# ✅ Dependencias de runtime: incluye WGET para el healthcheck
RUN apk add --no-cache libffi openssl wget

# Dependencias de compilación (temporales)
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    linux-headers \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo

# Instalar dependencias de Python
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apk del .build-deps  # ← Elimina build deps, pero wget se queda

# Copiar código de la app
COPY . .

# Crear usuario no root
RUN addgroup -S app && adduser -S app -G app && \
    chown -R app:app /app
USER app

EXPOSE 8081

# ✅ HEALTHCHECK ahora funciona porque wget está instalado
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:${PORT}/health || exit 1

# Iniciar con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "4", "--forwarded-allow-ips=*", "wsgi:app"]