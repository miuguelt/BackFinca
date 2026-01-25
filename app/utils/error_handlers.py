"""
Manejo centralizado de errores para la aplicación Flask
"""

from flask import jsonify, current_app, request
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_jwt_extended.exceptions import JWTExtendedException, CSRFError
from app.utils.security_logger import log_suspicious_activity, security_logger
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Registrar todos los manejadores de error centralizados"""
    
    from app.utils.response_handler import APIResponse

    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"Bad request: {error}")
        return APIResponse.error(
            message='Solicitud incorrecta',
            status_code=400,
            error_code='BAD_REQUEST',
            details={'error': str(error)}
        )

    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f"Unauthorized access attempt: {error}")
        return APIResponse.error(
            message='No autorizado',
            status_code=401,
            error_code='UNAUTHORIZED',
            details={'error': 'Credenciales inválidas o token expirado'}
        )

    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f"Forbidden access attempt: {error}")
        log_suspicious_activity(
            "Intento de acceso a recurso prohibido",
            severity='MEDIUM',
            additional_data={'error': str(error)}
        )
        return APIResponse.error(
            message='Acceso prohibido',
            status_code=403,
            error_code='FORBIDDEN',
            details={'error': 'No tienes permisos para acceder a este recurso'}
        )

    @app.errorhandler(404)
    def not_found(error):
        path = request.path
        method = request.method
        logger.info(f"Resource not found: {method} {path} - {error}")
        return APIResponse.error(
            message='Recurso no encontrado',
            status_code=404,
            error_code='NOT_FOUND',
            details={'error': 'El recurso solicitado no existe', 'path': path, 'method': method}
        )

    @app.errorhandler(405)
    def method_not_allowed(error):
        path = request.path
        method = request.method
        logger.warning(f"Method not allowed: {method} {path} - {error}")
        return APIResponse.error(
            message='Método no permitido',
            status_code=405,
            error_code='METHOD_NOT_ALLOWED',
            details={'error': 'El método HTTP usado no está permitido para este endpoint', 'path': path, 'method': method}
        )

    @app.errorhandler(409)
    def conflict(error):
        logger.warning(f"Data conflict: {error}")
        return APIResponse.error(
            message='Conflicto de datos',
            status_code=409,
            error_code='CONFLICT',
            details={'error': 'Los datos enviados entran en conflicto con el estado actual'}
        )

    @app.errorhandler(413)
    def request_entity_too_large(error):
        logger.warning(f"Request too large: {error}")
        log_suspicious_activity(
            "Intento de envío de payload excesivamente grande",
            severity='MEDIUM'
        )
        return APIResponse.error(
            message='Solicitud demasiado grande',
            status_code=413,
            error_code='PAYLOAD_TOO_LARGE',
            details={'error': 'El tamaño de los datos enviados excede el límite permitido'}
        )

    @app.errorhandler(422)
    def unprocessable_entity(error):
        logger.warning(f"Validation error: {error}")
        return APIResponse.error(
            message='Error de validación',
            status_code=422,
            error_code='VALIDATION_ERROR',
            details={'error': 'Los datos enviados no pasaron la validación'}
        )

    @app.errorhandler(429)
    def too_many_requests(error):
        logger.warning(f"Rate limit exceeded: {error}")
        log_suspicious_activity(
            "Límite de tasa excedido",
            severity='HIGH',
            additional_data={'error': str(error)}
        )
        return APIResponse.error(
            message='Demasiadas solicitudes',
            status_code=429,
            error_code='RATE_LIMIT_EXCEEDED',
            details={
                'error': 'Has excedido el límite de solicitudes permitidas',
                'retry_after': getattr(error, 'retry_after', 60)
            }
        )

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        
        # Rollback de transacciones en caso de error
        try:
            from app import db
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")

        return APIResponse.error(
            message='Error interno del servidor',
            status_code=500,
            error_code='INTERNAL_ERROR',
            details={'error': 'Ha ocurrido un error inesperado en el servidor'}
        )

    @app.errorhandler(502)
    def bad_gateway(error):
        logger.error(f"Bad gateway: {error}")
        return APIResponse.error(
            message='Error de gateway',
            status_code=502,
            error_code='BAD_GATEWAY',
            details={'error': 'Error de comunicación con servicios externos'}
        )

    @app.errorhandler(503)
    def service_unavailable(error):
        logger.error(f"Service unavailable: {error}")
        return APIResponse.error(
            message='Servicio no disponible',
            status_code=503,
            error_code='SERVICE_UNAVAILABLE',
            details={'error': 'El servicio está temporalmente no disponible'}
        )

    @app.errorhandler(504)
    def gateway_timeout(error):
        logger.error(f"Gateway timeout: {error}")
        return APIResponse.error(
            message='Timeout del gateway',
            status_code=504,
            error_code='GATEWAY_TIMEOUT',
            details={'error': 'El servidor tardó demasiado en responder'}
        )

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        logger.warning(f"Database integrity error: {error.orig}")
        
        try:
            from app import db
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")

        # Analizar el tipo de error de integridad
        error_message = str(error.orig)
        
        if 'UNIQUE constraint failed' in error_message or 'Duplicate entry' in error_message:
            message = 'Ya existe un registro con esos datos'
            code = 'duplicate_entry'
        elif 'FOREIGN KEY constraint failed' in error_message:
            message = 'No se puede completar la operación: datos relacionados no válidos'
            code = 'foreign_key_violation'
        elif 'NOT NULL constraint failed' in error_message:
            message = 'Faltan datos requeridos'
            code = 'missing_required_data'
        else:
            message = 'Error de integridad en los datos'
            code = 'integrity_error'

        return APIResponse.error(
            message=message,
            status_code=409,
            error_code=code.upper(),
            details={'error': 'Los datos no cumplen con las restricciones de la base de datos'}
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        logger.error(f"SQLAlchemy error: {error}", exc_info=True)
        
        try:
            from app import db
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")

        return APIResponse.error(
            message='Error de base de datos',
            status_code=500,
            error_code='DATABASE_ERROR',
            details={'error': 'Ha ocurrido un error al acceder a la base de datos'}
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        logger.warning(f"CSRF error: {error}")
        # Log del evento JWT/CSRF para seguridad
        try:
            from app.utils.security_logger import log_jwt_token_event
            log_jwt_token_event('ERROR', token_info={'csrf_error': str(error)})
        except Exception:
            pass

        return APIResponse.error(
            message='CSRF token inválido o ausente',
            status_code=401,
            error_code='CSRF_ERROR',
            details={'error': str(error)}
        )

    @app.errorhandler(JWTExtendedException)
    def handle_jwt_errors(error):
        logger.warning(f"JWT error: {error}")
        
        # Log del evento JWT para seguridad
        from app.utils.security_logger import log_jwt_token_event
        log_jwt_token_event('ERROR', token_info={'error': str(error)})
        
        return APIResponse.error(
            message='Error de autenticación',
            status_code=401,
            error_code='JWT_ERROR',
            details={'error': str(error)}
        )

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        logger.warning(f"Value error: {error}")
        return APIResponse.error(
            message='Error en los datos',
            status_code=400,
            error_code='VALUE_ERROR',
            details={'error': str(error)}
        )

    @app.errorhandler(KeyError)
    def handle_key_error(error):
        logger.warning(f"Key error: {error}")
        return APIResponse.error(
            message='Datos incompletos',
            status_code=400,
            error_code='MISSING_FIELD',
            details={'error': f'Falta el campo requerido: {str(error)}'}
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        
        # Log como actividad sospechosa si no es un error HTTP conocido
        if not isinstance(error, HTTPException):
            log_suspicious_activity(
                f"Excepción no manejada: {type(error).__name__}",
                severity='HIGH',
                additional_data={'error': str(error)}
            )

        # En desarrollo, mostrar más detalles
        if current_app.config.get('DEBUG', False):
            return APIResponse.error(
                message='Error no manejado',
                status_code=500,
                error_code='UNHANDLED_EXCEPTION',
                details={'error': str(error), 'type': type(error).__name__}
            )
        return APIResponse.error(
            message='Error interno del servidor',
            status_code=500,
            error_code='INTERNAL_ERROR',
            details={'error': 'Ha ocurrido un error inesperado'}
        )

def create_custom_abort(code, message, error_code=None, additional_data=None):
    """Función helper para crear abortos personalizados"""
    from app.utils.response_handler import APIResponse
    details = additional_data or {}
    return APIResponse.error(message=message, status_code=code, error_code=error_code or f'ERROR_{code}', details=details)
