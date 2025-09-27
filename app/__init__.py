from flask import Flask, request, jsonify, current_app, json, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from flask_cors import CORS
from flask_restx import Api
from datetime import timezone, datetime
from config import config
import logging
import sys
import os
import time
import jwt as pyjwt
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import text

from .utils.db_optimization import init_db_optimizations
from .utils.logging_config import configure_logging
from .utils.jwt_handlers import configure_jwt_handlers
from app.utils.response_handler import APIResponse

# Importar módulos de seguridad
from .utils.security_logger import setup_security_logging, log_authentication_attempt, log_jwt_token_event
from .utils.error_handlers import register_error_handlers
from .utils.rate_limiter import init_rate_limiter

# ====================================================================
# 1. Inicialización de extensiones (sin enlazarlas a la app aún)
# ====================================================================
db = SQLAlchemy()
jwt = JWTManager()

# ====================================================================
# 2. Funciones de ayuda y configuración modular
# ====================================================================
def configure_logging(app):
    """Configura el sistema de logging optimizado de la aplicación."""
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    
    # Formato mejorado de logging
    log_format = (
        '%(asctime)s - [%(levelname)s] - %(name)s - '
        '%(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Configurar handlers
    handlers = []
    
    # Handler para consola con colores
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # Handler para archivo si está habilitado
    if app.config.get('LOG_FILE_ENABLED', False):
        log_file = app.config.get('LOG_FILE', 'app.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configurar logging root
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True  # Sobrescribir configuración existente
    )
    
    # Configurar loggers específicos
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Logger para la aplicación
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    
    app_logger.info("Sistema de logging configurado exitosamente")

# (moved) configure_jwt_handlers defined in app.utils.jwt_handlers

# ====================================================================
# 3. La función principal de creación de la aplicación
# ====================================================================
def create_app(config_name='development'):
    # Prefer testing config when running under pytest to avoid touching dev DBs
    try:
        if config_name != 'testing' and ('PYTEST_CURRENT_TEST' in os.environ or 'pytest' in sys.modules):
            config_name = 'testing'
    except Exception:
        pass

    app = Flask(__name__)
    # Avoid automatic redirects on missing/extra trailing slashes which break CORS preflight (307 redirect not allowed)
    app.url_map.strict_slashes = False
    
    # Añade ProxyFix para entornos con proxies como Vercel o Nginx
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # Configurar el codificador JSON personalizado para toda la aplicación
    from app.utils.json_utils import JSONEncoder
    from app.utils.enum_registry import EnumJSONEncoder, register_application_enums
    import json as json_stdlib
    import enum
    
    # Registrar todos los enums de la aplicación
    register_application_enums()
    
    # Usar nuestro encoder personalizado para toda la aplicación
    app.json_encoder = EnumJSONEncoder
    
    # Forzar respuestas JSON (sin sobrescribir exportaciones CSV u otros binarios)
    @app.after_request
    def force_json_response(response):
        try:
            # No tocar si ya es JSON o es un tipo específico (csv, octet-stream, text/csv)
            if response.mimetype in ('application/json', 'text/csv', 'application/octet-stream'):
                return response
            # Detectar cuerpos JSON (dict/list serializados) cuando Flask ya convirtió dict -> JSON
            # Flask 3 ya establece application/json para dict; fallback por si un middleware lo altera
            data_prefix = (response.get_data(as_text=False) or b'')[:1]
            if data_prefix in (b'{', b'['):
                response.headers['Content-Type'] = 'application/json; charset=utf-8'
        except Exception:
            # Fallback silencioso: no bloquear la respuesta por un error menor
            pass
        return response

    @app.after_request
    def attach_access_token_to_json(response):
        """Inyecta access_token en el cuerpo JSON de TODAS las respuestas si está presente en Authorization o cookie HttpOnly.
        Esto permite que el frontend lo persista en localStorage y el interceptor lo envíe en Authorization.
        """
        try:
            # Detectar si es JSON o contiene JSON serializado
            data_bytes = response.get_data(as_text=False) or b''
            is_json_like = (response.mimetype and response.mimetype.startswith('application/json')) or (data_bytes[:1] in (b'{', b'['))
            if not is_json_like:
                return response

            # Extraer token de Authorization o cookie HttpOnly
            token = None
            try:
                auth = request.headers.get('Authorization', '')
                if isinstance(auth, str) and auth.lower().startswith('bearer '):
                    token = auth.split(' ', 1)[1].strip()
                if not token:
                    token = request.cookies.get('access_token_cookie')
            except Exception:
                token = None

            if not token:
                return response

            # Parsear el cuerpo, agregar access_token y re-serializar
            try:
                data_text = response.get_data(as_text=True) or ''
                payload = json.loads(data_text) if data_text else None
            except Exception:
                # Si no se puede parsear, no modificar
                return response

            if isinstance(payload, dict):
                payload['access_token'] = token
                response.set_data(json.dumps(payload))
                response.headers['Content-Type'] = 'application/json; charset=utf-8'
        except Exception:
            # No bloquear la respuesta por un error de inyección de token
            pass
        return response

    # Handlers globales básicos eliminados: ahora centralizados en app.utils.error_handlers

    # Flask-RESTX: forzar JSON en todos los endpoints
    from flask_restx import apidoc
    # apidoc.apidoc.add_resource = lambda *a, **kw: None  # Deshabilitar UI de Swagger si se desea solo JSON
    
    app_config = config.get(config_name, 'default')
    app.config.from_object(app_config)
    app.config['CONFIG_NAME'] = config_name

    # If using SQLite (tests / in-memory), remove SQLAlchemy engine options that
    # are incompatible with sqlite dialect (prevents errors during local checks).
    try:
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if isinstance(db_uri, str) and db_uri.startswith('sqlite'):
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    except Exception:
        pass

    # Configura el logging (antes de cualquier otra cosa)
    configure_logging(app)
    logger = logging.getLogger(__name__)

    logger.info("Initializing Flask app...")
    logger.debug(f"Using configuration: {config_name}")

    # Comentado: Evitar exponer URI de conexión con credenciales en logs
    # db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'No URI configurada')
    # logger.info(f"URI de conexión a la base de datos: {db_uri}")
    
    # Inicializa y enlaza las extensiones con la app
    db.init_app(app)
    jwt.init_app(app)
    
    # Inicializar optimizaciones de base de datos
    init_db_optimizations(app)
    logger.info("Database optimizations initialized")

    # Inicializar CORS y hooks relacionados (módulo utilitario)
    from app.utils.cors_setup import init_cors
    init_cors(app, logger)

    # Configurar JWT handlers mejorados
    configure_jwt_handlers(jwt)
    
    # Inicializar security logging
    setup_security_logging(app)
    
    # Registrar manejadores de error centralizados
    register_error_handlers(app)
    
    # Inicializar rate limiter (solo si está habilitado por configuración)
    limiter = None
    try:
        if app.config.get('RATE_LIMIT_ENABLED', True):
            limiter = init_rate_limiter(app)
            logger.info("Rate limiting habilitado por configuración")
        else:
            logger.info("Rate limiting desactivado por configuración")
    except Exception:
        logging.getLogger(__name__).exception('No se pudo inicializar el rate limiter')
    
    # Inicializar middlewares de optimización
    # request_middleware = RequestMiddleware(app)
    # security_middleware = SecurityMiddleware(app)
    # metrics_middleware = MetricsMiddleware(app)
    
    logger.info("Middlewares de optimización y seguridad inicializados")

    # Inicializar middlewares de seguridad (JWT global + debug logging)
    from app.utils.security_middleware import init_security_middlewares
    init_security_middlewares(app)

    # Registrar toda la API, namespaces y endpoints utilitarios desde módulo dedicado
    from app.api import register_api
    api = register_api(app, limiter)

    # ==============================================================
    # (moved) Dynamic schema/metadata and examples endpoints are now
    # provided by app.api.register_api under /api/v1/docs/*
    # ==============================================================

    # Bootstrap: crear usuario administrador semilla si no existe (movido a utilitario)
    try:
        from app.utils.bootstrap import seed_admin_user
        seed_admin_user(app, logger)
    except Exception:
        logger.exception('Fallo al ejecutar seed_admin_user')
    
    # Redirecciones públicas convenientes para documentación
    @app.route('/docs')
    @app.route('/docs/')
    def docs_redirect():
        """Redirigir a la documentación de la API versionada"""
        return redirect('/api/v1/docs/', code=302)

    @app.route('/swagger.json')
    def swagger_redirect():
        """Redirigir al JSON de Swagger versionado"""
        return redirect('/api/v1/swagger.json', code=302)

    # Ruta raíz pública
    @app.route('/', methods=['GET', 'OPTIONS'])
    def root_welcome():
        """Bienvenida pública en la raíz de la aplicación"""
        if request.method == 'OPTIONS':
            return '', 200
        return APIResponse.success(
            data={
                'message': 'Bienvenido al backend de la Finca Villaluz',
                'public': True,
                'endpoint': '/',
                'docs': '/api/v1/docs/'
            }
        )

    # Endpoint de health check público a nivel de aplicación (sin prefijo /api/v1)
    @app.route('/health', methods=['GET', 'OPTIONS'])
    def app_health():
        """Health check público accesible en /health (sin prefijo /api/v1)"""
        # Permitir preflight CORS
        if request.method == 'OPTIONS':
            return '', 200
        try:
            # Verificar conexión simple a la base de datos
            db.session.execute(text('SELECT 1'))
            db_status = 'healthy'
            status_code = 200
        except Exception as e:  # pragma: no cover - comportamiento en fallos
            db_status = f'unhealthy: {str(e)}'
            status_code = 503

        payload = {
            'success': True if status_code == 200 else False,
            'status': 'healthy' if status_code == 200 else 'unhealthy',
            'services': {
                'database': db_status
            },
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'uptime_seconds': time.time() - app.config.get('START_TIME', time.time()),
            'version': app.config.get('APP_VERSION', app.config.get('VERSION', '1.0.0')),
        }
        return jsonify(payload), status_code
    
    # ====================================================================
    # DOCUMENTACIÓN: Flask-RESTX genera automáticamente la documentación
    # Swagger en /swagger.json y la interfaz interactiva en /docs/
    # No se necesitan blueprints adicionales para documentación
    # ====================================================================
    
    # ====================================================================
    # NOTA: Se eliminaron todos los blueprints de routes antiguos
    # Ahora se usan exclusivamente los namespaces de Flask-RESTX
    # Esto proporciona mejor documentación, validación y organización
    # ====================================================================
    
    # (moved) debug request logging now initialized by app.utils.security_middleware.init_security_middlewares

    # Guardar tiempo de inicio
    app.config['START_TIME'] = time.time()
    
    logger.info("Flask app initialization complete.")
    return app