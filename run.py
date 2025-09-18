import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

from app import create_app, db
from flask import jsonify
from flask_jwt_extended.exceptions import JWTExtendedException
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import request
import logging

# Leer configuración desde argumentos de línea de comandos o variable de entorno
config_name = 'development'
if len(sys.argv) > 1 and sys.argv[1] == '--config' and len(sys.argv) > 2:
    config_name = sys.argv[2]
elif os.getenv('FLASK_ENV'):
    config_name = os.getenv('FLASK_ENV')

print(f"[RUN] Using configuration: {config_name}")
app = create_app(config_name)

# Aplicar ProxyFix si se ejecuta detrás de un reverse proxy (configurable vía env)
try:
    proxy_x_for = int(os.getenv('PROXY_FIX_X_FOR', '1'))
except Exception:
    proxy_x_for = 1
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_x_for, x_proto=int(os.getenv('PROXY_FIX_X_PROTO', '1')), x_host=int(os.getenv('PROXY_FIX_X_HOST', '1')), x_port=int(os.getenv('PROXY_FIX_X_PORT', '1')))

# Seguridad: encabezados HTTP básicos (también en desarrollo si se usa HTTPS)
@app.after_request
def set_security_headers(response):
    try:
        is_secure = request.is_secure or os.getenv('USE_HTTPS', 'true').lower() == 'true'
    except Exception:
        is_secure = False

    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'no-referrer')

    if is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

    return response

with app.app_context():
    # No crear tablas automáticamente en producción desde run.py
    if config_name != 'production' or os.getenv('FORCE_DB_CREATE', 'false').lower() == 'true':
        db.create_all()

# -------------------------------------------------------------
# Utilidad: resolver contexto SSL desde variables de entorno
# - Para evitar el error NET::ERR_CERT_AUTHORITY_INVALID en dev,
#   puedes generar un certificado confiable localmente (mkcert)
#   y apuntar las variables SSL_CERT_FILE y SSL_KEY_FILE.
# - Si no existen, se usa 'adhoc' como fallback.
# -------------------------------------------------------------

def _resolve_ssl_context():
    use_https = os.getenv('USE_HTTPS', 'true').lower() == 'true'
    if not use_https:
        print("[RUN] HTTPS desactivado (USE_HTTPS=false)")
        return None

    cert_file = os.getenv('SSL_CERT_FILE')
    key_file = os.getenv('SSL_KEY_FILE')

    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"[RUN] HTTPS con certificado provisto\n  CERT: {cert_file}\n  KEY : {key_file}")
        return (cert_file, key_file)

    print("[RUN] HTTPS con certificado adhoc (autofirmado)")
    return 'adhoc'


def _mask_secret_length(value):
    if not value:
        return '<empty>'
    try:
        return f'set (length={len(value)})'
    except Exception:
        return '<present>'


def log_startup_info(app, ssl_context):
    """Log masked startup information to help verify runtime characteristics.

    Avoid printing secrets; only emit lengths or existence flags.
    """
    logger = logging.getLogger('startup')
    logger.setLevel(logging.INFO)

    with app.app_context():
        cfg = app.config

        def _summarize_db_uri(uri):
            if not uri:
                return '<empty>'
            if '://' in uri:
                scheme = uri.split('://', 1)[0]
            else:
                scheme = 'unknown'
            return f'scheme={scheme}, length={len(uri)}'

        try:
            db_uri = cfg.get('SQLALCHEMY_DATABASE_URI')
        except Exception:
            db_uri = None

        jwt_secret_descr = _mask_secret_length(cfg.get('JWT_SECRET_KEY'))

        info = {
            'FLASK_ENV': os.getenv('FLASK_ENV', 'development'),
            'CONFIG_DEBUG': bool(cfg.get('DEBUG', False)),
            'PORT': int(os.getenv('PORT', 8081)),
            'USE_HTTPS': os.getenv('USE_HTTPS', 'true').lower() == 'true',
            'SSL_CONTEXT': 'provided' if isinstance(ssl_context, tuple) else ('adhoc' if ssl_context == 'adhoc' else 'none'),
            'DB': _summarize_db_uri(db_uri),
            'JWT_SECRET': jwt_secret_descr,
            'JWT_TOKEN_LOCATION': cfg.get('JWT_TOKEN_LOCATION'),
            'JWT_COOKIE_SECURE': cfg.get('JWT_COOKIE_SECURE'),
            'JWT_COOKIE_SAMESITE': cfg.get('JWT_COOKIE_SAMESITE'),
            'JWT_COOKIE_CSRF_PROTECT': cfg.get('JWT_COOKIE_CSRF_PROTECT'),
        }

        logger.info('Application startup summary:')
        for k, v in info.items():
            logger.info('  %s: %s', k, v)

        # Print a short sample of routes (limited to first 25)
        try:
            rules = sorted((r.rule for r in app.url_map.iter_rules()))
            sample = rules[:25]
            logger.info('  ROUTES (sample, limited to 25):')
            for r in sample:
                logger.info('    %s', r)
        except Exception:
            logger.info('  ROUTES: <could not enumerate>')


if __name__ == "__main__":
    # Lee el puerto desde las variables de entorno o usa 8081 por defecto
    port = int(os.environ.get('PORT', 8081))

    ssl_context = _resolve_ssl_context()  # Configurar HTTPS con certificados locales o adhoc

    # DEBUG: Log detallado de binding y SSL para troubleshooting localhost
    import socket
    try:
        # Resolver localhost para ver IPs asociadas
        localhost_ips = socket.getaddrinfo('localhost', port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        ip_list = [addr[4][0] for addr in localhost_ips]
        print(f"[DEBUG] Binding a 'localhost' resuelve a IPs: {ip_list}")
        print(f"[DEBUG] SSL Context: {ssl_context} (type: {type(ssl_context)})")
        
        if isinstance(ssl_context, tuple):
            cert_file, key_file = ssl_context
            print(f"[DEBUG] Cert file: {cert_file}, exists: {os.path.exists(cert_file)}")
            print(f"[DEBUG] Key file: {key_file}, exists: {os.path.exists(key_file)}")
    except Exception as e:
        print(f"[DEBUG] Error resolviendo localhost o SSL: {e}")

    # Log startup characteristics (masked) to help verify runtime config
    try:
        log_startup_info(app, ssl_context)
    except Exception as e:
        logging.getLogger('startup').exception('Failed to log startup info: %s', e)

    # NUEVO: Log de URL y puerto del backend en modo debug (run.py)
    try:
        scheme = 'https' if ssl_context else 'http'
        display_host = os.getenv('BACKEND_DISPLAY_HOST', 'localhost')
        logger = logging.getLogger('startup')
        msg = f"Backend escuchando en {scheme}://{display_host}:{port} (run.py)"
        print(f"[RUN] DEBUG: {msg}")
        logger.info("[RUN] DEBUG: %s", msg)
    except Exception:
        pass
    
    # DEBUG: Wrapper para loggear requests a /api/v1/docs
    from functools import wraps
    original_run = app.run

    @wraps(original_run)
    def debug_run(*args, **kwargs):
        # Interceptar requests para loggear host en /docs
        @app.before_request
        def log_request_debug():
            if request.path.startswith('/api/v1/docs'):
                print(f"[DEBUG DOCS] Request desde: {request.remote_addr}, Host header: {request.host}, Scheme: {request.scheme}, Path: {request.path}")
        
        return original_run(*args, **kwargs)

    app.run = debug_run

    # Ejecutar la app (HTTPS si ssl_context no es None)
    # Deshabilitar el debugger interactivo (use_debugger/use_evalex False) mientras permitimos el reloader
    # FIX: Cambiar binding a "127.0.0.1" para forzar IPv4 y evitar mismatch SSL con localhost (resuelve a IPv6)
    # Esto hace que https://localhost:8081 use IPv4, coincidiendo con el cert para 127.0.0.1
    app.run(host="127.0.0.1", port=port, debug=(config_name != 'production' and app.config.get('DEBUG', False)), ssl_context=ssl_context, use_debugger=False, use_evalex=False, use_reloader=True)