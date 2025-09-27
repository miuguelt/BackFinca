import os
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import request, jsonify
import logging
from flask_jwt_extended.exceptions import JWTExtendedException

# Detectar entorno y cargar el archivo .env apropiado
flask_env = os.getenv('FLASK_ENV')
if flask_env == 'production':
    load_dotenv('.env.production')
    config_name = 'production'
else:
    load_dotenv()  # Carga .env por defecto
    config_name = os.getenv('FLASK_ENV', 'development')

from app import create_app, db
app = create_app(config_name)

# Log en tiempo de importación para despliegues WSGI (cuando no se ejecuta __main__)
try:
    display_host = os.getenv('BACKEND_DISPLAY_HOST', 'localhost')
    display_port = int(os.getenv('PORT', 8081))
    # Permitir forzar esquema de visualización, si no, inferir por USE_HTTPS
    scheme = os.getenv('BACKEND_DISPLAY_SCHEME') or ('https' if os.getenv('USE_HTTPS', 'true').lower() == 'true' else 'http')
    print(f"[WSGI] IMPORT: Backend address hint: {scheme}://{display_host}:{display_port} (wsgi.py; el bind real lo gestiona el servidor WSGI/proxy)")
    logging.getLogger('startup').info(
        '[WSGI] IMPORT: Backend address hint: %s://%s:%s (wsgi.py; el bind real lo gestiona el servidor WSGI/proxy)',
        scheme, display_host, display_port
    )
except Exception:
    pass

# Aplicar ProxyFix si se ejecuta detrás de un reverse proxy (configurable vía env)
try:
    proxy_x_for = int(os.getenv('PROXY_FIX_X_FOR', '1'))
except Exception:
    proxy_x_for = 1
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_x_for, x_proto=int(os.getenv('PROXY_FIX_X_PROTO', '1')), x_host=int(os.getenv('PROXY_FIX_X_HOST', '1')), x_port=int(os.getenv('PROXY_FIX_X_PORT', '1')))

# Seguridad: encabezados HTTP seguros (aplicar en producción y en HTTPS)
@app.after_request
def set_security_headers(response):
    try:
        is_secure = request.is_secure or os.getenv('USE_HTTPS', 'true').lower() == 'true'
    except Exception:
        is_secure = False

    # Evitar exponer información sensible
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'no-referrer')
    response.headers.setdefault('X-XSS-Protection', '1; mode=block')

    # HSTS - aplicar sólo si HTTPS está habilitado y estamos en producción
    if (config_name == 'production' or is_secure):
        response.headers.setdefault('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload')
        # CSP: base estricta por defecto, relajada únicamente para rutas de documentación
        path = (request.path or '').rstrip('/')
        is_docs = path.startswith('/api/v1/docs') or path.startswith('/swaggerui')
        if is_docs:
            # SwaggerUI requiere inline scripts/estilos y carga de assets desde CDN (jsdelivr)
            csp = "; ".join([
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "script-src-elem 'self' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "style-src-elem 'self' https://cdn.jsdelivr.net",
                "img-src 'self' data:",
                "font-src 'self' https://cdn.jsdelivr.net data:",
                "connect-src 'self'",
                "worker-src 'self' blob:",
                "frame-ancestors 'self'",
            ])
        else:
            csp = "; ".join([
                "default-src 'self'",
                "object-src 'none'",
                "img-src 'self'",
                "font-src 'self'",
                "style-src 'self'",
                "script-src 'self'",
                "connect-src 'self'",
                "frame-ancestors 'self'",
            ])
        # Sobrescribir para asegurar la política correcta
        response.headers['Content-Security-Policy'] = csp

    return response

# Evitar ejecutar db.create_all automáticamente en producción
with app.app_context():
    if config_name != 'production' or os.getenv('FORCE_DB_CREATE', 'false').lower() == 'true':
        db.create_all()

def _resolve_ssl_context():
    use_https = os.getenv('USE_HTTPS', 'true').lower() == 'true'
    if not use_https:
        return None

    cert_file = os.getenv('SSL_CERT_FILE')
    key_file = os.getenv('SSL_KEY_FILE')

    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        return (cert_file, key_file)

    # No generar ni usar certificado 'adhoc' en producción
    if config_name == 'production':
        logging.warning('No se encontraron certificados SSL y estamos en producción; SSL no será activado por el app directamente. Configure un reverse proxy con certificados.')
        return None

    return 'adhoc'


# Startup sanity checks
if config_name == 'production':
    # Ensure JWT_SECRET_KEY is not a placeholder and has sufficient length (32 bytes hex -> 64 chars)
    jwt_secret = os.getenv('JWT_SECRET_KEY') or app.config.get('JWT_SECRET_KEY')
    if not jwt_secret or jwt_secret.lower().startswith(('change_me', 'replace_with', 'dev', 'default')) or len(jwt_secret) < 64:
        logging.error('Invalid JWT_SECRET_KEY for production: please set a secure 32-byte hex secret in environment variable JWT_SECRET_KEY')
        # Fail fast to avoid running with insecure config
        raise SystemExit(1)
    # Ensure cookie domain set
    if not os.getenv('JWT_COOKIE_DOMAIN') and not app.config.get('JWT_COOKIE_DOMAIN'):
        logging.error('JWT_COOKIE_DOMAIN is not set for production environment. Set JWT_COOKIE_DOMAIN to your base domain (e.g. isladigital.xyz)')
        raise SystemExit(1)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8081))
    ssl_context = _resolve_ssl_context()

    # NUEVO: Log de URL y puerto del backend en producción (wsgi.py)
    try:
        scheme = 'https' if ssl_context else 'http'
        display_host = os.getenv('BACKEND_DISPLAY_HOST', 'localhost')
        logger = logging.getLogger('startup')
        msg = f"Backend escuchando en {scheme}://{display_host}:{port} (wsgi.py)"
        print(f"[WSGI] PROD: {msg}")
        logger.info("[WSGI] PROD: %s", msg)
    except Exception:
        pass

    # Deshabilitar el debugger interactivo incluso si DEBUG=True
    app.run(host="0.0.0.0", port=port, debug=False, ssl_context=ssl_context, use_debugger=False, use_evalex=False)

@app.errorhandler(JWTExtendedException)
def handle_jwt_errors(e):
    return jsonify({"error": str(e)}), 401