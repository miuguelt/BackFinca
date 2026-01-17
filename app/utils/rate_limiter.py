"""
Configuración de rate limiting para la aplicación.
"""

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.utils.response_handler import APIResponse
from app.utils.security_logger import log_rate_limit_exceeded

import logging

logger = logging.getLogger(__name__)
_RATE_LIMITER_STORAGE_OK = None
_GLOBAL_LIMITER = None


def get_user_id():
    """Obtener ID de usuario para rate limiting personalizado."""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        return user_id if user_id else get_remote_address()
    except Exception:
        return get_remote_address()


def get_remote_address_with_forwarded():
    """Obtener dirección IP considerando proxy forwarding."""
    forwarded_ip = request.environ.get("HTTP_X_FORWARDED_FOR")
    if forwarded_ip:
        return forwarded_ip.split(",")[0].strip()
    return request.environ.get("REMOTE_ADDR", "127.0.0.1")


def rate_limit_handler(request_limit):
    """Handler personalizado para límites excedidos (respuesta estandarizada)."""
    endpoint = request.endpoint or "unknown"
    user_id = get_user_id()

    try:
        log_rate_limit_exceeded(endpoint=endpoint, limit=str(request_limit), user_identifier=user_id)
    except Exception:
        logger.exception("Fallo al registrar evento de rate limit")

    logger.warning("Rate limit exceeded for %s on %s", user_id, endpoint)

    return APIResponse.error(
        message="Límite de solicitudes excedido",
        status_code=429,
        error_code="RATE_LIMIT_EXCEEDED",
        details={
            "limit": str(request_limit),
            "endpoint": endpoint,
            "retry_after_seconds": 60,
        },
    )


def init_rate_limiter(app):
    global _GLOBAL_LIMITER, _RATE_LIMITER_STORAGE_OK
    if _GLOBAL_LIMITER is not None:
        return _GLOBAL_LIMITER
    storage_uri = app.config.get("RATE_LIMIT_STORAGE_URI")

    if not storage_uri:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address_with_forwarded,
            default_limits=["10000 per day", "1000 per hour"],
            on_breach=rate_limit_handler,
            storage_uri="memory://",
            headers_enabled=True,
            swallow_errors=True,
            in_memory_fallback_enabled=True,
        )
        app.logger.info("Rate limiter inicializado con storage: memory:// (sin configuración de REDIS_URL)")
        _GLOBAL_LIMITER = limiter
        return limiter

    if _RATE_LIMITER_STORAGE_OK is None:
        try:
            from redis import Redis
            redis_client = Redis.from_url(storage_uri)
            redis_client.ping()
            _RATE_LIMITER_STORAGE_OK = True
        except Exception as e:
            app.logger.warning("Rate limiter Redis '%s' falló: %s. Reintentando con memory://", storage_uri, e)
            _RATE_LIMITER_STORAGE_OK = False

    if _RATE_LIMITER_STORAGE_OK:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address_with_forwarded,
            default_limits=["10000 per day", "1000 per hour"],
            on_breach=rate_limit_handler,
            storage_uri=storage_uri,
            headers_enabled=True,
            swallow_errors=True,
            in_memory_fallback_enabled=True,
        )
        app.logger.info("Rate limiter inicializado con storage Redis: %s", storage_uri)
        _GLOBAL_LIMITER = limiter
        return limiter
    else:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address_with_forwarded,
            default_limits=["10000 per day", "1000 per hour"],
            on_breach=rate_limit_handler,
            storage_uri="memory://",
            headers_enabled=True,
            swallow_errors=True,
            in_memory_fallback_enabled=True,
        )
        app.logger.info("Rate limiter inicializado con storage: memory:// (fallback)")
        _GLOBAL_LIMITER = limiter
        return limiter


RATE_LIMIT_CONFIG = {
    "auth": {
        "login": "10 per minute",
        "refresh": "20 per minute",
        "logout": "30 per minute",
        "change_password": "20 per hour",
        "recover": "5 per hour",
        "reset": "5 per hour",
    },
    "users": {"create": "10 per hour", "read": "500 per hour", "update": "100 per hour", "delete": "20 per hour"},
    "animals": {"create": "100 per hour", "read": "1000 per hour", "update": "200 per hour", "delete": "50 per hour"},
    "activity": {
        "summary": "120 per minute",
        "stats": "120 per minute",
        "filters": "60 per minute",
    },
    "general": {"read": "500 per hour", "write": "100 per hour", "admin": "2000 per hour"},
}
