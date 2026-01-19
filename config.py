import os
from dotenv import load_dotenv
from datetime import timedelta
import logging
from urllib.parse import quote_plus

# Cargar variables de entorno desde .env antes de leer la configuracion.
load_dotenv(override=True)

# Helper para parsear CORS_ORIGINS desde variables de entorno (.env)
# Admite formato JSON (p.ej. ["https://a.com","http://b.com"]) o CSV (a.com,b.com)
# Retorna una lista de strings o None si no se definió.
def _parse_cors_origins_env():
    raw = os.getenv('CORS_ORIGINS')
    if not raw:
        return None
    try:
        raw_stripped = raw.strip()
        # Si es JSON array
        if raw_stripped.startswith('['):
            import json as _json
            data = _json.loads(raw_stripped)
            if isinstance(data, list):
                items = []
                for x in data:
                    if not isinstance(x, str):
                        x = str(x)
                    s = x.strip().strip("\"'`").strip('`')
                    if s:
                        items.append(s)
                # dedupe preservando orden
                seen = set()
                deduped = []
                for it in items:
                    if it not in seen:
                        deduped.append(it)
                        seen.add(it)
                return deduped
    except Exception:
        pass
    # Fallback: CSV
    items = [s.strip().strip("\"'`").strip('`') for s in raw.split(',')]
    items = [s for s in items if s]
    seen = set()
    deduped = []
    for it in items:
        if it not in seen:
            deduped.append(it)
            seen.add(it)
    return deduped or None


def _build_sqlalchemy_database_uri():
    """Build SQLALCHEMY_DATABASE_URI from DB_* env vars when not provided."""
    uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    if uri:
        return uri

    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT') or '3306'
    name = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')

    if not all([host, name, user, password]):
        return None

    try:
        safe_user = quote_plus(user)
        safe_password = quote_plus(password)
    except Exception:
        safe_user = user
        safe_password = password

    return f"mysql+pymysql://{safe_user}:{safe_password}@{host}:{port}/{name}"


class Config:
    """Configuración base de la aplicación. Aplica a todos los entornos."""

    # -----------------------
    # Base de Datos
    # -----------------------
    HOST = os.getenv('DB_HOST')
    PORT = os.getenv('DB_PORT') or '3306'
    DATABASE = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_DRIVER = 'pymysql'  # pymysql | mysqldb | mysqlconnector
    SQLALCHEMY_DATABASE_URI = _build_sqlalchemy_database_uri()
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("SQLALCHEMY_DATABASE_URI o DB_* (DB_HOST/DB_NAME/DB_USER/DB_PASSWORD) es requerido")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Connection Pool optimizado para alta concurrencia
        'pool_size': 20,  # Conexiones permanentes (reducido de 25)
        'max_overflow': 30,  # Conexiones adicionales (reducido de 40)
        'pool_timeout': 30,  # Timeout para obtener conexión (aumentado de 20)
        'pool_recycle': 1800,  # Reciclar cada 30 min (reducido de 3600 para evitar stale connections)
        'pool_pre_ping': True,  # Verificar conexiones antes de usar
        'echo': False,
        'connect_args': {
            'charset': 'utf8mb4',
            'autocommit': False,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30,
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
        }
    }

    # Si se usa SQLite, eliminar opciones de pool incompatibles
    _maybe_db_uri = SQLALCHEMY_DATABASE_URI
    if isinstance(_maybe_db_uri, str) and _maybe_db_uri.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {}

    # -----------------------
    # Cache & Rendimiento
    # -----------------------
    REDIS_URL = os.getenv('REDIS_URL')
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL') or REDIS_URL
    CACHE_TYPE = 'redis' if CACHE_REDIS_URL else 'simple'
    CACHE_IGNORE_ERRORS = True
    CACHE_DEFAULT_TIMEOUT = 600
    CACHE_THRESHOLD = 1000
    PERFORMANCE_MONITORING = True
    SLOW_QUERY_THRESHOLD = 0.5
    QUERY_CACHE_ENABLED = True
    QUERY_CACHE_TIMEOUT = 600
    QUERY_CACHE_MAX_SIZE = 500
    # SSE: límite de conexiones por IP (el endpoint /api/v1/events respeta este valor)
    SSE_MAX_CONN_PER_IP = int(os.getenv('SSE_MAX_CONN_PER_IP') or '3')

    # Activity feed caching (perfil/analytics)
    ACTIVITY_SUMMARY_CACHE_TTL = int(os.getenv('ACTIVITY_SUMMARY_CACHE_TTL', '60'))
    ACTIVITY_STATS_CACHE_TTL = int(os.getenv('ACTIVITY_STATS_CACHE_TTL', '60'))
    ACTIVITY_FILTERS_CACHE_TTL = int(os.getenv('ACTIVITY_FILTERS_CACHE_TTL', '120'))

    # -----------------------
    # Compresión
    # -----------------------
    COMPRESS_MIMETYPES = [
        'text/html', 'text/css', 'text/xml', 'application/json',
        'application/javascript', 'text/javascript', 'application/xml'
    ]
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500

    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY es requerido en todos los entornos")

    JWT_TOKEN_LOCATION = ['cookies', 'headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_COOKIE_HTTPONLY = True
    # IMPORTANT: nunca permitir nombres de cookie None/vacíos porque Werkzeug explota
    # cuando intenta hacer dump_cookie() con key=None.
    JWT_ACCESS_COOKIE_NAME = (os.getenv('JWT_ACCESS_COOKIE_NAME') or 'access_token_cookie').strip()
    JWT_REFRESH_COOKIE_NAME = (os.getenv('JWT_REFRESH_COOKIE_NAME') or 'refresh_token_cookie').strip()
    JWT_ACCESS_CSRF_COOKIE_NAME = (os.getenv('JWT_ACCESS_CSRF_COOKIE_NAME') or 'csrf_access_token').strip()
    JWT_REFRESH_CSRF_COOKIE_NAME = (os.getenv('JWT_REFRESH_CSRF_COOKIE_NAME') or 'csrf_refresh_token').strip()
    if not JWT_ACCESS_COOKIE_NAME or not JWT_REFRESH_COOKIE_NAME:
        raise ValueError("JWT_ACCESS_COOKIE_NAME y JWT_REFRESH_COOKIE_NAME no pueden estar vacíos")
    JWT_COOKIE_SAMESITE = 'None'
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_BLOCKLIST_ENABLED = True
    JWT_BLOCKLIST_TOKEN_CHECKS = ['access', 'refresh']

    # -----------------------
    # Bootstrap / Warmup (arranque)
    # -----------------------
    def _env_bool(name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return str(raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

    # Semilla de admin y warmup pueden disparar tormenta de conexiones al iniciar.
    SEED_ADMIN_ENABLED = _env_bool('SEED_ADMIN_ENABLED', default=False)
    CACHE_WARMUP_ENABLED = _env_bool('CACHE_WARMUP_ENABLED', default=False)
    CACHE_WARMUP_LIMIT = int(os.getenv('CACHE_WARMUP_LIMIT') or 10)

    # -----------------------
    # CORS
    # -----------------------
    CORS_ORIGINS = _parse_cors_origins_env() or []
    # Deprecated: usar solo CORS_ORIGINS desde .env; no se fusionan extras
    CORS_EXTRA_ORIGINS = []

    # -----------------------
    # Seguridad / JSON
    # -----------------------
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    JSON_SORT_KEYS = False
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    JSONIFY_MIMETYPE = 'application/json; charset=utf-8'

    # -----------------------
    # Uploads de Archivos
    # -----------------------
    UPLOAD_FOLDER = 'static/uploads'
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
    MAX_IMAGES_PER_ANIMAL = 20

    # -----------------------
    # Rate Limiting
    # -----------------------
    RATE_LIMIT_STORAGE_URI = os.getenv('RATE_LIMIT_STORAGE_URI') or REDIS_URL
    RATE_LIMIT_ENABLED = True

    # -----------------------
    # Logging Seguridad
    # -----------------------
    SECURITY_LOG_ENABLED = True
    SECURITY_LOG_LEVEL = logging.INFO
    LOG_LEVEL = logging.INFO
    LOG_FILE_ENABLED = False

    # -----------------------
    # Flags de características
    # -----------------------
    # Permite habilitar la creación pública de usuarios incluso si ya existen
    # usuarios en la base de datos. Úsese con precaución.
    PUBLIC_USER_CREATION_ENABLED = os.getenv('PUBLIC_USER_CREATION_ENABLED', 'true').lower() == 'true'

    # -----------------------
    # Email (SMTP)
    # -----------------------
    EMAIL_ENABLED = _env_bool('EMAIL_ENABLED', default=True)
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT') or 587)
    SMTP_USERNAME = os.getenv('SMTP_USERNAME') or os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_USE_TLS = _env_bool('SMTP_USE_TLS', default=True)
    SMTP_USE_SSL = _env_bool('SMTP_USE_SSL', default=False)
    SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL') or SMTP_USERNAME
    SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME') or ''
    SMTP_TIMEOUT = int(os.getenv('SMTP_TIMEOUT') or 10)
    PASSWORD_RESET_URL = os.getenv('PASSWORD_RESET_URL')
    FRONTEND_PASSWORD_RESET_PATH = os.getenv('FRONTEND_PASSWORD_RESET_PATH') or '/reset-password'

    # -----------------------
    # URLs
    # -----------------------
    API_BASE_URL = os.getenv('API_BASE_URL')
    API_HOST = os.getenv('API_HOST')
    API_PORT = os.getenv('API_PORT')
    API_PROTOCOL = os.getenv('API_PROTOCOL')
    FRONTEND_URL = os.getenv('FRONTEND_URL')
    FRONTEND_HOST = os.getenv('FRONTEND_HOST')
    FRONTEND_PORT = os.getenv('FRONTEND_PORT')
    FRONTEND_PROTOCOL = os.getenv('FRONTEND_PROTOCOL')
    BACKEND_URL = os.getenv('BACKEND_URL')
    BACKEND_HOST = os.getenv('BACKEND_HOST')
    BACKEND_PORT = os.getenv('BACKEND_PORT')
    BACKEND_PROTOCOL = os.getenv('BACKEND_PROTOCOL')
    API_BASE_URL_NO_VERSION = os.getenv('API_BASE_URL_NO_VERSION')
    API_DOCS_URL = os.getenv('API_DOCS_URL')
    API_SWAGGER_URL = os.getenv('API_SWAGGER_URL')

class DevelopmentConfig(Config):
    """Configuración para desarrollo (localhost)."""
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    RATE_LIMIT_ENABLED = False
    
    # JWT - Desarrollo local: usar HTTPS local para permitir Secure + SameSite=None
    from os import getenv as _getenv
    JWT_COOKIE_SECURE = _getenv('DEV_JWT_COOKIE_SECURE', 'true').lower() == 'true'
    JWT_COOKIE_SAMESITE = 'None'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    
    # JWT_COOKIE_DOMAIN debe ser None para que el navegador use el dominio actual
    JWT_COOKIE_DOMAIN = None
    
    # Configuración adicional para desarrollo
    JWT_COOKIE_PATH = '/'

    # Plan B: permitir desactivar temporalmente la protección CSRF de cookies JWT para validar el flujo de refresh.
    # Usa DEV_JWT_COOKIE_CSRF_PROTECT=true para reactivar cuando terminemos la validación.
    JWT_COOKIE_CSRF_PROTECT = _getenv('DEV_JWT_COOKIE_CSRF_PROTECT') == 'true'
    # Permitir uso de JWT tanto en cookies como en encabezados para facilitar pruebas
    JWT_TOKEN_LOCATION = ['cookies', 'headers']

    # Allow small clock skew when decoding tokens to avoid "Signature has expired"
    # errors caused by minor time differences between clients and server.
    # Value is in seconds.
    JWT_DECODE_LEEWAY = 30
    
    # CORS - Solo desde variable de entorno
    CORS_ORIGINS = _parse_cors_origins_env() or []
    # SSE: en desarrollo, reducir el límite para forzar disciplina en el cliente
    SSE_MAX_CONN_PER_IP = int(os.getenv('SSE_MAX_CONN_PER_IP') or '1')

class ProductionConfig(Config):
    """Configuración para producción (HTTPS)."""
    DEBUG = False
    LOG_LEVEL = logging.INFO
    
    # Configuraciones de seguridad más estrictas en producción
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB en producción (más restrictivo)
    
    # JWT - Atributos específicos de producción
    # JWT_COOKIE_SECURE debe ser True para HTTPS
    JWT_COOKIE_SECURE = True  # Cookies seguras para producción
    JWT_COOKIE_SAMESITE = 'None'  # Ajustar según necesidad
    # Importante: no forzar un dominio fijo. Debe venir del entorno
    # para coincidir con el dominio real desplegado (p. ej. .enlinea.sbs).
    # Si no se define, wsgi.py abortará el arranque en producción.
    JWT_COOKIE_DOMAIN = os.getenv('JWT_COOKIE_DOMAIN')
    JWT_TOKEN_LOCATION = ['cookies', 'headers']  # Usar cookies y headers para JWT
    JWT_COOKIE_CSRF_PROTECT = True  # Proteger cookies JWT con CSRF (recomendado en producción)

    # CORS - Solo desde variable de entorno
    CORS_ORIGINS = _parse_cors_origins_env() or []

    # Ajustar el pool de MySQL según límites del servidor
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 12,  # Suficiente para 3-4 workers gthread (4 threads)
        'max_overflow': 8,  # Bursts controlados sin saturar MySQL
        'pool_timeout': 30,  # Tiempo de espera para obtener una conexión
        'pool_recycle': 1800,  # Reciclar conexiones cada 30 minutos
        'pool_pre_ping': True
    }
    
    @classmethod
    def validate_production_env(cls):
        """Valida variables de entorno requeridas para producción"""
        if not os.getenv('JWT_SECRET_KEY'):
            raise ValueError("La variable JWT_SECRET_KEY DEBE estar definida en producción.")
        if not os.getenv('JWT_COOKIE_DOMAIN'):
            raise ValueError("La variable JWT_COOKIE_DOMAIN DEBE estar definida en producción.")
    
    # El dominio de la cookie debe ser el dominio principal (con punto inicial)
    # para que sea válido en cualquier subdominio
    JWT_COOKIE_DOMAIN = os.getenv('JWT_COOKIE_DOMAIN')
    
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # Allow a small leeway for token decoding to tolerate minor clock skew.
    # Production servers should have accurate time (NTP) configured.
    JWT_DECODE_LEEWAY = 30

    # CORS - Solo desde variable de entorno
    CORS_ORIGINS = _parse_cors_origins_env() or []

class TestingConfig(Config):
    """Configuración específica para pruebas."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    JWT_COOKIE_CSRF_PROTECT = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    DEBUG = False
    LOG_LEVEL = logging.DEBUG
    RATE_LIMIT_ENABLED = True
    # Forzar uso de headers en testing ya que las cookies no funcionan bien en entorno de pruebas
    JWT_TOKEN_LOCATION = ['headers']
    # Permitir usar una BD distinta en pruebas por defecto (db 2)
    REDIS_URL = os.getenv('TEST_REDIS_URL')
    CACHE_REDIS_URL = os.getenv('TEST_CACHE_REDIS_URL') or REDIS_URL
    CACHE_TYPE = 'redis' if CACHE_REDIS_URL else 'simple'
    RATE_LIMIT_STORAGE_URI = os.getenv('TEST_RATE_LIMIT_STORAGE_URI')

# Diccionario de configuración final
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
