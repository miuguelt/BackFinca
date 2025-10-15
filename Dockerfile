###############
# Dockerfile optimizado para Flask + Gunicorn
# - Elimina CMD duplicado
# - Instala solo dependencias necesarias en Alpine
# - Usa build deps temporales para compilar cryptography/psutil y luego las elimina
# - Usa usuario no root
# - Añade healthcheck básico (¡ahora con wget instalado!)
###############

FROM python:3.12-alpine AS app

# Variables de entorno Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081

WORKDIR /app

# Dependencias de runtime: openssl, libffi y wget (¡necesario para el healthcheck!)
RUN apk add --no-cache libffi openssl wget

# Dependencias de build temporales para compilar cryptography / psutil
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    linux-headers \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo

# Copiar solo requirements primero para aprovechar la caché de capas
COPY requirements.txt ./

# Instalar dependencias de Python y limpiar build deps
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apk del .build-deps

# Copiar el resto del código de la aplicación
COPY . .

# Crear usuario no root y asignar permisos
RUN addgroup -S app && adduser -S app -G app && \
    chown -R app:app /app

USER app

EXPOSE 8081

# Healthcheck: ahora wget está disponible
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:${PORT}/health || exit 1

# Iniciar la app con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "4", "--forwarded-allow-ips=*", "wsgi:app"]