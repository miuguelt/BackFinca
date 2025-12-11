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
SQLALCHEMY_DATABASE_URI=mysql+pymysql://finca:changeme@localhost:3306/finca

# Redis / caché / rate limit
REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_URL=${REDIS_URL}
RATE_LIMIT_STORAGE_URI=${REDIS_URL}
RATE_LIMIT_ENABLED=true

# Seguridad
JWT_SECRET_KEY=super-secret-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# URLs de referencia
API_BASE_URL=http://localhost:8081/api/v1
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8081
```
Notas:
- En desarrollo `JWT_SECRET_KEY` se genera solo si no existe, pero define uno explícito para compartir sesiones entre instancias.
- Si usas HTTPS en local, añade `SSL_CERT_FILE` y `SSL_KEY_FILE` apuntando a tus certificados.

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
