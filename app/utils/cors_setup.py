"""
Configuración de CORS y hooks auxiliares.
"""
from flask import request, current_app
from flask_cors import CORS
import logging


def _sanitize_origins(origins):
    raw_origins = origins or []
    sanitized = []
    for o in raw_origins:
        if not isinstance(o, str):
            continue
        s = o.strip()
        if s and s[0] in ("'", '"', '`') and s[-1:] == s[0] and len(s) >= 2:
            s = s[1:-1].strip()
        s = s.strip('`')
        if s:
            sanitized.append(s)
    # Deduplicar preservando orden
    seen = set()
    deduped = []
    for origin in sanitized:
        if origin not in seen:
            deduped.append(origin)
            seen.add(origin)
    return deduped


def init_cors(app, logger: logging.Logger = None):
    """Inicializa CORS, handlers de preflight y logging relacionado."""
    logger = logger or logging.getLogger(__name__)

    # Usar exclusivamente los orígenes definidos en app.config['CORS_ORIGINS']
    try:
        app.config['CORS_ORIGINS'] = _sanitize_origins(app.config.get('CORS_ORIGINS', []) or [])
    except Exception:
        pass

    # Configura CORS con los orígenes (ya consolidados)
    CORS(
        app,
        origins=app.config.get('CORS_ORIGINS', []),
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin",
            "Cache-Control",
            "X-File-Name",
            "X-CSRF-Token",
            "X-CSRF-TOKEN",  # variante en mayúsculas usada por Swagger/otros clientes
            "X-App-Version",
            "X-Client-Timezone",
            "X-Client-Locale",
            "ngrok-skip-browser-warning"
        ],
        expose_headers=[
            "Content-Range",
            "X-Content-Range",
            "X-Total-Count",
            "Authorization",
            "ETag",
            "Last-Modified",
            "Cache-Control",
            "X-API-Version",
            "X-Cache-Strategy",
            "X-Has-More",
            "Vary"
        ],
        supports_credentials=True,
        max_age=86400
    )

    # Log detallado de CORS para depuración y manejo explícito de preflight
    @app.before_request
    def _handle_cors_preflight():
        if request.method == "OPTIONS":
            from flask import make_response
            logger.debug(
                "CORS preflight -> path: %s, origin: %s, req-method: %s, req-headers: %s",
                request.path,
                request.headers.get('Origin'),
                request.headers.get('Access-Control-Request-Method'),
                request.headers.get('Access-Control-Request-Headers'),
            )
            res = make_response()
            origin = request.headers.get('Origin')
            allowed_origins = current_app.config.get('CORS_ORIGINS', []) or []
            if origin and origin in allowed_origins:
                res.headers.add('Access-Control-Allow-Origin', origin)
            req_headers = request.headers.get('Access-Control-Request-Headers')
            if req_headers:
                res.headers.add('Access-Control-Allow-Headers', req_headers)
            allowed_methods = current_app.config.get('CORS_METHODS', ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"])
            res.headers.add('Access-Control-Allow-Methods', ', '.join(allowed_methods))
            res.headers.add('Access-Control-Allow-Credentials', 'true')
            res.headers.add('Access-Control-Max-Age', str(current_app.config.get('CORS_MAX_AGE', 86400)))
            res.headers.add('Vary', 'Origin')
            return res

    @app.after_request
    def _add_cors_headers_and_log(response):
        def _merge_vary(value: str):
            existing = response.headers.get('Vary')
            parts = []
            if existing:
                parts.extend([p.strip() for p in existing.split(',') if p.strip()])
            parts.extend([p.strip() for p in (value or '').split(',') if p.strip()])
            seen = set()
            merged = []
            for p in parts:
                if p not in seen:
                    merged.append(p)
                    seen.add(p)
            if merged:
                response.headers['Vary'] = ', '.join(merged)

        origin = request.headers.get('Origin')
        allowed_origins = current_app.config.get('CORS_ORIGINS', []) or []
        if origin and origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            _merge_vary('Origin')
        elif origin and origin not in allowed_origins:
            logger.warning(
                "CORS: Origin %s no está en CORS_ORIGINS. Agregue '%s' a la variable CORS_ORIGINS en .env",
                origin,
                origin
            )
        if request.method != 'OPTIONS':
            logger.debug(
                "Response -> path: %s, status: %s, origin: %s, A-C-Allow-Origin: %s",
                request.path,
                response.status,
                origin,
                response.headers.get('Access-Control-Allow-Origin'),
            )
        return response

    # Log de configuración CORS/JWT para facilitar el diagnóstico en arranque
    try:
        allowed_origins = app.config.get('CORS_ORIGINS', [])
        logger.info(f"CORS habilitado. Orígenes permitidos (solo .env): {allowed_origins}")
        logger.info(
            "CORS detalles -> supports_credentials: %s, methods: %s, allow_headers: %s, expose_headers: %s, max_age: %s",
            True,
            ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
            [
                "Content-Type", "Authorization", "X-Requested-With", "Accept",
                "Origin", "Cache-Control", "X-File-Name", "X-CSRF-Token", "X-CSRF-TOKEN",
                "X-App-Version", "X-Client-Timezone", "X-Client-Locale",
                "ngrok-skip-browser-warning"
            ],
            ["Content-Range", "X-Content-Range", "X-Total-Count", "Authorization"],
            86400,
        )
        logger.info(
            "JWT cookies -> domain: %s, secure: %s, samesite: %s, token_location: %s",
            app.config.get('JWT_COOKIE_DOMAIN'),
            app.config.get('JWT_COOKIE_SECURE'),
            app.config.get('JWT_COOKIE_SAMESITE'),
            app.config.get('JWT_TOKEN_LOCATION'),
        )
    except Exception as e:
        logger.warning(f"No se pudo registrar configuración CORS/JWT en logs: {e}")
