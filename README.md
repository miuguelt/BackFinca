# BackFinca – Backend Flask

API REST para Finca Villaluz con módulos de analytics, gestión de animales y optimizaciones de rendimiento. Este README está orientado a desarrolladores para levantar el entorno rápido, correr pruebas y entender la estructura básica.

## Pila rápida
- Python 3.11, Flask + Flask-RESTX, SQLAlchemy, Flask-Migrate
- MySQL/MariaDB como base de datos principal
- Redis para caché y rate limiting
- Gunicorn como servidor WSGI en producción (puerto 8081 por defecto)

## Prerrequisitos
- Python 3.11+
- MySQL 8+ (o MariaDB equivalente)
- Redis 6+
- Opcional: mkcert u otro método para certificados locales si quieres HTTPS real en dev

## Configuración de entorno (.env de ejemplo)
```env
FLASK_ENV=development
PORT=8081
USE_HTTPS=false           # true si tienes certificados locales

# Base de datos
DB_HOST=localhost
DB_PORT=3306
DB_NAME=finca
DB_USER=finca
DB_PASSWORD=changeme

# Redis / caché / rate limit
REDIS_URL=redis://localhost:6379/0

# Seguridad
JWT_SECRET_KEY=super-secret-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# URLs de referencia
API_BASE_URL=http://localhost:8081/api/v1
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8081
```
Notas:
- JWT_SECRET_KEY es requerido en todos los entornos; usa un valor seguro.
- SQLALCHEMY_DATABASE_URI es opcional; si no se define se arma con DB_*.
- Si usas HTTPS en local, anade SSL_CERT_FILE y SSL_KEY_FILE apuntando a tus certificados.

## Levantar en local (sin Docker)
1) Crear entorno y dependencias
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2) Variables de entorno: crea tu `.env` con el bloque anterior.
3) Base de datos: crea la BD y usuario. Luego aplica migraciones:
```bash
FLASK_ENV=development flask --app wsgi db upgrade
```
4) Ejecutar la API en modo dev (HTTP):
```bash
USE_HTTPS=false PORT=8081 FLASK_ENV=development python run.py
```
   - HTTPS adhoc: quita `USE_HTTPS=false` y deja que `run.py` genere un certificado adhoc.
5) La API expone health en `/api/v1/health` y toda la ruta base en `/api/v1`.

## Levantar con Docker
```bash
# Requiere Docker y docker-compose; provee las mismas variables en .env
docker compose up --build
```
El servicio publica en `8081`. Asegúrate de tener listas las redes externas configuradas en `docker-compose.yaml` o ajústalas a tu entorno.

## Disponibilidad y reinicio (playbook)
Objetivo: que el backend se reinicie automaticamente ante caidas y tenga chequeos de salud claros.

Opciones recomendadas (elige una):
1) Docker Compose (ya configurado):
   - `docker-compose.yaml` usa `restart: unless-stopped`.
   - `Dockerfile` incluye `HEALTHCHECK` contra `/api/v1/health`.
   - Sugerencia: si el orquestador soporta, vincula healthcheck a reinicio automatico.
2) systemd (VM o bare metal):
   - Crea un servicio `backfinca.service` con:
     - `Restart=always`, `RestartSec=5`
     - `ExecStart=gunicorn --preload --workers 2 --threads 2 --bind 0.0.0.0:8081 wsgi:app`
     - `EnvironmentFile=/ruta/.env`
   - Agrega `StartLimitIntervalSec` y `StartLimitBurst` para evitar bucles de reinicio.
3) Supervisor (alternativa ligera):
   - `autorestart=true`, `startretries=3`, `stderr_logfile` y `stdout_logfile` habilitados.

Recomendaciones de resiliencia:
- Mantener `/health` y `/api/v1/health` como checks de liveness y readiness.
- Usar `pool_pre_ping` en SQLAlchemy (ya habilitado) para recuperar conexiones caidas.
- Evitar `--preload` si haces tareas pesadas al iniciar (warmup/seed).
- Configurar `--max-requests` y `--max-requests-jitter` en Gunicorn (ya en Dockerfile) para mitigar leaks.

Alertas y observabilidad:
- Centraliza logs de Gunicorn + app (stdout/stderr).
- Usa `trace_id` de las respuestas de error para diagnostico.

Sugerencia: no reiniciar el proceso desde el propio Flask. La supervision debe hacerla el orquestador (Docker, systemd o Supervisor).

## Migraciones y scripts útiles
- Migraciones ORM: `flask --app wsgi db upgrade` / `flask --app wsgi db migrate -m "mensaje"`.
- Índices de rendimiento adicionales: `python run_migration.py` (usa `add_performance_indexes.sql`).

## Pruebas
- Ejecutar suite: `pytest -q`.
- Configura un DB/Redis de pruebas (`FLASK_ENV=testing` o `PYTEST_CURRENT_TEST` se detecta automáticamente).

## Documentación
Todo el material está en `docs/`. Consulta `docs/README.md` para un índice por temas (overview, backend, frontend, analytics, optimizaciones, migraciones y pruebas).

## Estructura mínima del proyecto
- `run.py` / `wsgi.py`: entrada de la app (dev/prod).
- `app/`: código fuente (namespaces, modelos, utils, cache, JWT, rate limiting).
- `migrations/`: historial de Alembic.
- `docs/`: documentación organizada por área.

