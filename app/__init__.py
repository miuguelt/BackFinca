from flask import Flask, request, jsonify, current_app, json, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, unset_jwt_cookies
from flask_cors import CORS
from flask_restx import Api
from flask_caching import Cache
from flask_migrate import Migrate
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
from app.extensions.db import init_db_session_management, get_db

# Importar módulos de seguridad
from .utils.security_logger import setup_security_logging, log_authentication_attempt, log_jwt_token_event
from .utils.error_handlers import register_error_handlers
from .utils.rate_limiter import init_rate_limiter
from .utils.db_protector import init_db_protector

# ====================================================================
# 1. Inicialización de extensiones (sin enlazarlas a la app aún)
# ====================================================================
db = SQLAlchemy()
jwt = JWTManager()
cache = Cache()
migrate = Migrate()

_LOGGING_CONFIGURED = False
_CACHE_HEALTHCHECK_DONE = False
_APP_REGISTRY = {}

# ====================================================================
# 2. Funciones de ayuda y configuración modular
# ====================================================================
def configure_logging(app):
    """Configura el sistema de logging optimizado de la aplicación."""
    # Integración con Gunicorn: reutilizar exclusivamente sus handlers para evitar duplicados
    try:
        if ('gunicorn' in sys.modules) or os.getenv('GUNICORN_CMD_ARGS') or (os.getenv('SERVER_SOFTWARE') or '').lower().startswith('gunicorn'):
            gunicorn_error_logger = logging.getLogger('gunicorn.error')
            root = logging.getLogger()
            if gunicorn_error_logger and gunicorn_error_logger.handlers:
                # Reutilizar exclusivamente handlers de gunicorn
                root.handlers = gunicorn_error_logger.handlers
                root.setLevel(gunicorn_error_logger.level)
                app.logger.handlers = gunicorn_error_logger.handlers
                app.logger.setLevel(gunicorn_error_logger.level)
                app.logger.propagate = False  # evitar doble emisión hacia root
                # Reducir ruido de loggers verbosos
                logging.getLogger('werkzeug').setLevel(logging.WARNING)
                logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
                app.logger.info("Logging integrado con Gunicorn (usando handlers del master).")
                return
    except Exception:
        pass
    # Fallback: no añadir handlers; confiar en configuración del entorno/WSGI
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    root = logging.getLogger()
    root.setLevel(log_level)
    app.logger.handlers = []
    app.logger.setLevel(log_level)
    app.logger.propagate = True
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    app.logger.info("Logging fallback sin handlers propios (sin Gunicorn).")

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
    global _APP_REGISTRY
    _key = config_name
    _existing = _APP_REGISTRY.get(_key)
    if _existing:
        return _existing

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
        """Inyecta access_token en el cuerpo JSON de respuestas específicas si está presente en Authorization o cookie HttpOnly.
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
                    cookie_name = current_app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token_cookie')
                    token = request.cookies.get(cookie_name)
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
                # No inyectar token en respuestas que ya tienen estructura de APIResponse
                # con campos específicos como 'success', 'data', 'message', 'error'
                if 'success' in payload and ('data' in payload or 'error' in payload):
                    # Es una respuesta de APIResponse, no inyectar token para evitar conflictos
                    return response
                
                # Inyectar token solo en respuestas que no son de APIResponse
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

    if not _LOGGING_CONFIGURED:
        configure_logging(app)
        globals()['_LOGGING_CONFIGURED'] = True
    logger = logging.getLogger(__name__)

    logger.info("Initializing Flask app...")
    logger.debug(f"Using configuration: {config_name}")

    # Comentado: Evitar exponer URI de conexión con credenciales en logs
    # db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'No URI configurada')
    # logger.info(f"URI de conexión a la base de datos: {db_uri}")
    
    # Inicializa y enlaza las extensiones con la app
    db.init_app(app)
    jwt.init_app(app)
    init_db_session_management(app, db)
    
    # Inicializar protector de base de datos (seguridad proactiva)
    init_db_protector(app, db)
    
    # Inicializar caché con fallback robusto si Redis no está disponible
    try:
        cache_config = {
            'CACHE_TYPE': app.config.get('CACHE_TYPE', 'redis'),
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 600),
            'CACHE_THRESHOLD': app.config.get('CACHE_THRESHOLD', 1000),
            'CACHE_IGNORE_ERRORS': app.config.get('CACHE_IGNORE_ERRORS', True),
        }
        if cache_config['CACHE_TYPE'] == 'redis':
            cache_config['CACHE_REDIS_URL'] = app.config.get('CACHE_REDIS_URL') or app.config.get('REDIS_URL')
        cache.init_app(app, config=cache_config)

        # Si se usa Redis, realizar una verificación de salud del backend de caché
        if cache_config['CACHE_TYPE'] == 'redis' and not _CACHE_HEALTHCHECK_DONE:
            try:
                _k = '__cache_health__'
                cache.set(_k, 'ok', timeout=5)
                _v = cache.get(_k)
                if _v != 'ok':
                    raise RuntimeError('Redis cache set/get comprobación fallida')
                logger.info('Redis cache inicializado correctamente')
                globals()['_CACHE_HEALTHCHECK_DONE'] = True
            except Exception as e:
                logger.warning(f'Redis no disponible, aplicando fallback a SimpleCache: {e}')
                cache.init_app(app, config={
                    'CACHE_TYPE': 'simple',
                    'CACHE_DEFAULT_TIMEOUT': cache_config['CACHE_DEFAULT_TIMEOUT'],
                    'CACHE_IGNORE_ERRORS': True,
                })
                logger.info('SimpleCache inicializado como fallback')
    except Exception:
        logger.exception('Error inicializando caché; usando SimpleCache por seguridad')
        cache.init_app(app, config={
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 600),
            'CACHE_IGNORE_ERRORS': True,
        })

    migrate.init_app(app, db)

    # Inicializar optimizaciones de base de datos
    init_db_optimizations(app)
    logger.info("Database optimizations initialized")

    # Inicializar CORS y hooks relacionados (módulo utilitario)
    from app.utils.cors_setup import init_cors
    init_cors(app, logger)

    # Compresión gzip para respuestas JSON/text (sin dependencias externas)
    try:
        from app.utils.compression import init_compression
        init_compression(app)
    except Exception:
        logger.exception("No se pudo inicializar compresión gzip")

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

    # Bootstrap: crear usuario administrador semilla si no existe (opcional)
    # En producci¢n conviene ejecutarlo como tarea post-deploy/CLI para evitar
    # tormenta de conexiones con m£ltiples workers.
    try:
        seed_enabled = app.config.get('SEED_ADMIN_ENABLED', False)
        if seed_enabled:
            from app.utils.bootstrap import seed_admin_user
            seed_admin_user(app, logger)
            logger.info('SEED_ADMIN_ENABLED activo; seed_admin_user ejecutado')
        else:
            logger.info('SEED_ADMIN_ENABLED desactivado; se omite seed_admin_user')
    except Exception:
        logger.exception('Fallo al ejecutar seed_admin_user')

    # Warmup de caché para acelerar primera carga (controlado por config)
    try:
        # Check explicitly for False to allow disabling in testing
        warmup_enabled = app.config.get('CACHE_WARMUP_ENABLED', False)
        # Evitar warmup durante comandos CLI (migraciones, etc.) para no tocar tablas incompletas.
        try:
            if os.environ.get('FLASK_RUN_FROM_CLI') == 'true':
                warmup_enabled = False
        except Exception:
            pass
        if hasattr(app.config, 'get') and app.config['CONFIG_NAME'] == 'testing':
             warmup_enabled = False

        if warmup_enabled:
            from app.utils.bootstrap import warmup_initial_caches
            warmup_initial_caches(app, logger)
            logger.info('Warmup de caché inicial ejecutado')
        else:
            logger.info('CACHE_WARMUP_ENABLED desactivado; se omite warmup')
    except Exception:
        logger.exception('Fallo al ejecutar warmup_initial_caches')
    
    # Redirecciones públicas convenientes para documentación
    @app.route('/docs')
    def docs_redirect():
        """Redirigir a la documentación de la API versionada"""
        return redirect('/api/v1/docs/', code=302)

    @app.route('/swagger.json')
    def swagger_redirect():
        """Redirigir al JSON de Swagger versionado"""
        return redirect('/api/v1/swagger.json', code=302)

    # Ruta para servir archivos estáticos (imágenes subidas)
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Servir archivos estáticos (imágenes, etc.)"""
        static_folder = os.path.join(app.root_path, '..', 'static')
        return send_from_directory(static_folder, filename)
    
    # Ruta pública específica para imágenes de animales (sin autenticación)
    @app.route('/public/images/<path:filename>')
    def serve_public_images(filename):
        """Servir imágenes de animales públicamente sin autenticación"""
        images_folder = os.path.join(app.root_path, '..', 'static', 'uploads')
        return send_from_directory(images_folder, filename)

    # Endpoint público para obtener URLs de imágenes de un animal
    @app.route('/public/animal-images/<int:animal_id>', methods=['GET'])
    def get_public_animal_images(animal_id):
        """Obtener URLs públicas de imágenes de un animal sin autenticación"""
        try:
            from app.models.animals import Animals
            from app.models.animal_images import AnimalImages
            
            # Verificar que el animal existe
            animal = Animals.query.get(animal_id)
            if not animal:
                return jsonify({
                    'success': False,
                    'message': f'Animal con ID {animal_id} no encontrado'
                }), 404
            
            # Obtener imágenes ordenadas (primero la principal, luego por fecha)
            images = AnimalImages.query.filter_by(animal_id=animal_id)\
                .order_by(AnimalImages.is_primary.desc(), AnimalImages.created_at.desc())\
                .all()
            
            # Serializar con URLs públicas
            images_data = []
            for image in images:
                # Generar URL dinámica usando el host actual
                scheme = 'https' if request.is_secure else 'http'
                base_url = f"{scheme}://{request.host}"
                
                # Extraer la ruta relativa del filepath (quitar 'static/uploads/')
                relative_path = image.filepath
                if relative_path.startswith('static/uploads/'):
                    relative_path = relative_path[len('static/uploads/'):]
                
                # Generar URL usando el endpoint público
                image_url = f"{base_url}/public/images/{relative_path}"
                
                images_data.append({
                    'id': image.id,
                    'filename': image.filename,
                    'filepath': image.filepath,
                    'url': image_url,
                    'is_primary': image.is_primary,
                    'created_at': image.created_at.isoformat() if image.created_at else None
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'animal_id': animal_id,
                    'total': len(images_data),
                    'images': images_data
                },
                'message': f'{len(images_data)} imagen(es) encontrada(s)'
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error al obtener imágenes: {str(e)}'
            }), 500

    # Ruta raíz pública
    @app.route('/', methods=['GET', 'OPTIONS'])
    def root_welcome():
        """Bienvenida pública en la raíz de la aplicación"""
        if request.method == 'OPTIONS':
            return '', 200
        # Respuesta simple que además instruye al navegador a limpiar cualquier cookie JWT previa
        resp_body, status_code = APIResponse.success(
            message='Bienvenido al backend de la Finca Villaluz. Autenticación limpiada para nueva sesión.',
            data={'auth_cleared': True}
        )
        resp = jsonify(resp_body)
        unset_jwt_cookies(resp)
        resp.status_code = status_code
        resp.headers['Cache-Control'] = 'no-store'
        return resp

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
    
    @app.route('/db-check-session', methods=['GET'])
    def app_db_check_session():
        try:
            with get_db() as session:
                session.execute(text('SELECT 1'))
            return jsonify({'success': True, 'status': 'healthy'}), 200
        except Exception as e:
            return jsonify({'success': False, 'status': f'unhealthy: {str(e)}'}), 503
    
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
    _APP_REGISTRY[_key] = app
    return app
