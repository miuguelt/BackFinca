import os
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import request, jsonify, current_app
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

# En producción, asegurar que las URLs generadas usen https
if config_name == 'production':
    try:
        app.config.setdefault('PREFERRED_URL_SCHEME', 'https')
    except Exception:
        pass

# Log en tiempo de importación para despliegues WSGI (cuando no se ejecuta __main__)
try:
    display_host = os.getenv('BACKEND_DISPLAY_HOST', 'localhost')
    display_port = int(os.getenv('PORT', 8081))
    # Permitir forzar esquema de visualización, si no, inferir por USE_HTTPS (por defecto https en producción y http en desarrollo)
    _default_https = 'true' if config_name == 'production' else 'false'
    scheme = os.getenv('BACKEND_DISPLAY_SCHEME') or ('https' if os.getenv('USE_HTTPS', _default_https).lower() == 'true' else 'http')
    print(f"[WSGI] IMPORT: Backend address hint: {scheme}://{display_host}:{display_port} (wsgi.py; el bind real lo gestiona el servidor WSGI/proxy)")
    logging.getLogger('startup').info(
        '[WSGI] IMPORT: Backend address hint: %s://%s:%s (wsgi.py; el bind real lo gestiona el servidor WSGI/proxy)',
        scheme, display_host, display_port
    )
except Exception:
    pass

# Nota: ProxyFix ya se aplica dentro de create_app. Evitamos duplicarlo aquí

# Seguridad: encabezados HTTP seguros (aplicar en producción y en HTTPS)
@app.after_request
def set_security_headers(response):
    try:
        _default_https = 'true' if config_name == 'production' else 'false'
        is_secure = request.is_secure or os.getenv('USE_HTTPS', _default_https).lower() == 'true'
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
        is_docs = path.startswith('/api/v1/docs') or path.startswith('/swaggerui') or path.startswith('/docs')
        if is_docs:
            # SwaggerUI requiere inline scripts/estilos y carga de assets desde CDN (jsdelivr)
            # Ampliamos CSP para permitir recursos necesarios en producción
            csp = "; ".join([
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
                "script-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
                "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
                "img-src 'self' data: blob: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
                "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com data:",
                "connect-src *",
                "worker-src 'self' blob:",
                "frame-src 'self' blob:",
                "frame-ancestors 'self'",
            ])
        else:
            # Permitir conexiones salientes hacia orígenes definidos en CORS_ORIGINS además de 'self'
            try:
                allowed_origins = current_app.config.get('CORS_ORIGINS', []) or []
            except Exception:
                allowed_origins = []
            connect_src_values = ["'self'"] + allowed_origins
            csp = "; ".join([
                "default-src 'self'",
                "object-src 'none'",
                "img-src 'self'",
                "font-src 'self'",
                "style-src 'self'",
                "script-src 'self'",
                f"connect-src {' '.join(connect_src_values)}",
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
    # En desarrollo, desactivar HTTPS por defecto para evitar problemas con certificados 'adhoc'.
    _default_https = 'true' if config_name == 'production' else 'false'
    use_https = os.getenv('USE_HTTPS', _default_https).lower() == 'true'
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