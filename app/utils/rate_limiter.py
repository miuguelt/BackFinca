"""
Configuración de rate limiting para la aplicación
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.utils.security_logger import log_rate_limit_exceeded
import logging

logger = logging.getLogger(__name__)


def get_user_id():
    """Obtener ID de usuario para rate limiting personalizado"""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        return user_id if user_id else get_remote_address()
    except Exception:
        return get_remote_address()


def get_remote_address_with_forwarded():
    """Obtener dirección IP considerando proxy forwarding"""
    forwarded_ip = request.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_ip:
        return forwarded_ip.split(',')[0].strip()
    return request.environ.get('REMOTE_ADDR', '127.0.0.1')


def rate_limit_handler(request_limit):
    """Handler personalizado para límites excedidos"""
    endpoint = request.endpoint or 'unknown'
    user_id = get_user_id()

    # Log del evento
    try:
        log_rate_limit_exceeded(
            endpoint=endpoint,
            limit=str(request_limit),
            user_identifier=user_id
        )
    except Exception:
        logger.exception("Fallo al registrar evento de rate limit")

    logger.warning(f"Rate limit exceeded for {user_id} on {endpoint}")

    # Respuesta personalizada
    from flask import jsonify
    return jsonify({
        'message': 'Límite de solicitudes excedido',
        'error': f'Has excedido el límite de {request_limit} para este endpoint',
        'code': 'rate_limit_exceeded',
        'retry_after': 60
    }), 429


def init_rate_limiter(app):
    """Inicializar y configurar el rate limiter"""
    # Usar la URL de Redis configurada en la aplicación
    storage_uri = app.config.get('RATE_LIMIT_STORAGE_URI')
    redis_url = app.config.get('REDIS_URL')
    
    # Si no se configuró RATE_LIMIT_STORAGE_URI pero sí REDIS_URL, usar REDIS_URL
    if not storage_uri and redis_url:
        storage_uri = redis_url
        app.config['RATE_LIMIT_STORAGE_URI'] = storage_uri
    
    # Si todavía no hay storage_uri, usar Redis por defecto
    if not storage_uri:
        storage_uri = 'redis://localhost:6379/0'
        app.config['RATE_LIMIT_STORAGE_URI'] = storage_uri
    
    try:
        # Validar que Redis está disponible antes de usarlo como storage
        from redis import Redis
        
        redis_client = Redis.from_url(storage_uri)
        # PING anticipado para detectar credenciales o conectividad inválida
        redis_client.ping()
        
        limiter = Limiter(
            app=app,
            key_func=get_remote_address_with_forwarded,
            default_limits=["10000 per day", "1000 per hour"],
            on_breach=rate_limit_handler,
            storage_uri=storage_uri,
            headers_enabled=True,
        )
        app.logger.info(f"Rate limiter inicializado con storage Redis: {storage_uri}")
        return limiter
    except Exception as e:
        # Fallback a almacenamiento en memoria si Redis no está disponible
        app.logger.warning(f"Rate limiter Redis '{storage_uri}' fallo: {e}. Reintentando con memory://")
        limiter = Limiter(
            app=app,
            key_func=get_remote_address_with_forwarded,
            default_limits=["10000 per day", "1000 per hour"],
            on_breach=rate_limit_handler,
            storage_uri='memory://',
            headers_enabled=True,
        )
        app.logger.info("Rate limiter inicializado con storage: memory:// (fallback)")
        return limiter


# Configuración de rate limiting por defecto por tipo de endpoint
RATE_LIMIT_CONFIG = {
    'auth': {
        'login': "10 per minute",
        'refresh': "20 per minute",
        'logout': "30 per minute",
        'change_password': "20 per hour",
        'recover': "5 per hour",
        'reset': "5 per hour",
    },
    'users': {'create': "10 per hour", 'read': "500 per hour", 'update': "100 per hour", 'delete': "20 per hour"},
    'animals': {'create': "100 per hour", 'read': "1000 per hour", 'update': "200 per hour", 'delete': "50 per hour"},
    'general': {'read': "500 per hour", 'write': "100 per hour", 'admin': "2000 per hour"}
}
