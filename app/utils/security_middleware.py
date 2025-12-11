"""
Middlewares de seguridad y utilidades asociadas.
"""
import logging
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def init_security_middlewares(app):
    logger = logging.getLogger('app.auth')

    # Protección global con JWT para endpoints (excepto lista blanca)
    @app.before_request
    def enforce_jwt_protection():
        # Permitir preflight CORS
        if request.method == 'OPTIONS':
            return
        # Normalizar path quitando barra final para comparar correctamente
        raw_path = request.path or ''
        path = raw_path.rstrip('/') or '/'
        public_paths = {
            '/api/v1/auth/login',
            '/api/v1/auth/refresh',
            '/api/v1/auth/public-confirm',
            '/api/v1/health',
            '/api/v1',  # raíz pública del blueprint
            '/',        # raíz de la app accesible sin JWT
            '/health',
            '/favicon.ico',  # permitir favicon sin JWT
            '/api/v1/docs',
            '/api/v1/docs/schema',
            '/api/v1/docs/examples',
            '/api/v1/docs/guia-frontend',  # nueva guía pública
            '/api/v1/docs/guia-frontend-html',
            '/api/v1/swagger.json',
            # Rutas raíz generadas por Flask-RESTX para Swagger
            '/swagger.json',
            # Rutas raíz de conveniencia para UI
            '/docs',
            # Permitir assets de Swagger UI sin JWT
            '/api/v1/swaggerui',
            '/api/v1/swaggerui/',
            '/api/v1/swaggerui/o2c.html',
            # Permitir archivos estáticos (imágenes, CSS, JS) sin JWT
            '/static',
            # Permitir imágenes públicas sin JWT
            '/public',
        }
        # Permitir recursos estáticos de Swagger UI y documentación sin JWT (wildcards)
        if (
            path.startswith('/api/v1/swaggerui/')
            or path.startswith('/swaggerui/')
            or raw_path.startswith('/api/v1/docs/')  # cubrir /api/v1/docs/*
            or path.startswith('/static/')  # permitir todos los archivos estáticos
            or path.startswith('/public/')  # permitir imágenes públicas y endpoints públicos
        ):
            return

        # Permitir la creación de usuarios sin JWT (rutas públicas controladas)
        if request.method == 'POST' and path in ('/api/v1/users', '/api/v1/users/public'):
            return
            
        # Permitir rutas públicas sin JWT
        if path in public_paths:
            return
        try:
            verify_jwt_in_request()
            # Autorización por rol: solo Administrador puede hacer PUT/DELETE
            if request.method in ('PUT', 'DELETE'):
                from flask_jwt_extended import get_jwt
                user_id = get_jwt_identity()
                user_claims = get_jwt() if user_id else {}
                role = user_claims.get('role')
                if role != 'Administrador':
                    return jsonify({'msg': 'Forbidden: Admin role required'}), 403
        except Exception as e:
            # Diagnóstico detallado de la causa del fallo de autenticación
            from app.utils.response_handler import APIResponse
            err_cls = e.__class__.__name__
            msg_map = {
                'NoAuthorizationError': 'Token ausente (header/cookie no presente)',
                'ExpiredSignatureError': 'Token expirado',
                'FreshTokenRequired': 'Se requiere token fresco',
                'RevokedTokenError': 'Token revocado',
                'UserLoadError': 'Error cargando usuario para el token'
            }
            human_msg = msg_map.get(err_cls, 'Token faltante o inválido')
            # Comentado: Evitar exponer información sensible en logs de JWT
            # logger.debug(
            #     'JWT verification failed: %s -> %s path=%s auth_header_present=%s cookies=%s',
            #     err_cls, str(e), raw_path, bool(request.headers.get('Authorization')),
            #     list(request.cookies.keys()) if request.cookies else []
            # )
            logger.debug('JWT verification failed for path: %s', raw_path)
            # Expiracin de token: estandarizar respuesta para que el frontend pueda actuar
            if err_cls == 'ExpiredSignatureError':
                return APIResponse.error(
                    'Token expirado',
                    status_code=401,
                    error_code='TOKEN_EXPIRED',
                    details={
                        'exception_class': err_cls,
                        'exception': str(e),
                        'path': raw_path,
                        'client_action': 'CLEAR_AUTH_AND_RELOGIN',
                        'should_clear_auth': True,
                        'logout_url': '/api/v1/auth/logout'
                    }
                )
            return APIResponse.error(
                human_msg,
                status_code=401,
                error_code="JWT_ERROR",
                details={
                    'exception_class': err_cls,
                    'exception': str(e),
                    'path': raw_path
                }
            )

    # Logging de debug selectivo
    @app.before_request
    def log_request_info():
        if app.config.get('DEBUG', False):
            if any(path in request.path for path in ['/login', '/refresh', '/protected', '/debug']):
                logger.debug(f"REQUEST: {request.method} {request.path}")
                logger.debug(f"Headers: {dict(request.headers)}")
                if request.cookies:
                    logger.debug(f"Cookies present: {list(request.cookies.keys())}")
