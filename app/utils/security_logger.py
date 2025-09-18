"""
Módulo de logging de seguridad para auditoría y monitoreo
"""

import logging
from datetime import datetime, timezone
from flask import request, current_app
from functools import wraps
import json

# Configurar logger específico para seguridad
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Handler para archivo de seguridad (si está habilitado)
def setup_security_logging(app):
    """Configurar logging de seguridad"""
    if app.config.get('SECURITY_LOG_ENABLED', True):
        # Handler para archivo de seguridad
        security_handler = logging.FileHandler('security.log')
        security_handler.setLevel(logging.INFO)
        
        # Formato específico para logs de seguridad
        security_formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        security_logger.addHandler(security_handler)

def get_client_info():
    """Obtener información del cliente para logs"""
    return {
        'ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR')),
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'endpoint': request.endpoint,
        'method': request.method,
        'path': request.path
    }

def log_authentication_attempt(user_identifier, success, additional_info=None):
    """Log de intentos de autenticación"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'AUTHENTICATION_ATTEMPT',
        'user_identifier': user_identifier,
        'success': success,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    if additional_info:
        log_data['additional_info'] = additional_info
    
    if success:
        security_logger.info(f"LOGIN_SUCCESS: {json.dumps(log_data)}")
    else:
        security_logger.warning(f"LOGIN_FAILED: {json.dumps(log_data)}")

def log_authorization_failure(user_id, required_role, user_role, resource):
    """Log de fallos de autorización"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'AUTHORIZATION_FAILURE',
        'user_id': user_id,
        'required_role': required_role,
        'user_role': user_role,
        'resource': resource,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    security_logger.warning(f"AUTHORIZATION_DENIED: {json.dumps(log_data)}")

def log_data_access(user_id, action, resource, resource_id=None):
    """Log de acceso a datos sensibles"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'DATA_ACCESS',
        'user_id': user_id,
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    security_logger.info(f"DATA_ACCESS: {json.dumps(log_data)}")

def log_suspicious_activity(description, severity='MEDIUM', additional_data=None):
    """Log de actividad sospechosa"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'SUSPICIOUS_ACTIVITY',
        'description': description,
        'severity': severity,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    if additional_data:
        log_data['additional_data'] = additional_data
    
    if severity == 'HIGH':
        security_logger.error(f"SUSPICIOUS_ACTIVITY: {json.dumps(log_data)}")
    else:
        security_logger.warning(f"SUSPICIOUS_ACTIVITY: {json.dumps(log_data)}")

def log_rate_limit_exceeded(endpoint, limit, user_identifier=None):
    """Log de límites de tasa excedidos"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'RATE_LIMIT_EXCEEDED',
        'endpoint': endpoint,
        'limit': limit,
        'user_identifier': user_identifier,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    security_logger.warning(f"RATE_LIMIT_EXCEEDED: {json.dumps(log_data)}")

def security_audit(action_type):
    """Decorador para auditar acciones de seguridad"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                # Log successful action
                log_data = {
                    'event': 'SECURITY_ACTION',
                    'action_type': action_type,
                    'function': f.__name__,
                    'success': True,
                    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                }
                security_logger.info(f"SECURITY_ACTION: {json.dumps(log_data)}")
                return result
            except Exception as e:
                # Log failed action
                log_data = {
                    'event': 'SECURITY_ACTION',
                    'action_type': action_type,
                    'function': f.__name__,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                }
                security_logger.error(f"SECURITY_ACTION_FAILED: {json.dumps(log_data)}")
                raise
        return decorated_function
    return decorator

def log_admin_action(user_id, action, target_resource, target_id=None, changes=None):
    """Log de acciones administrativas"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'ADMIN_ACTION',
        'user_id': user_id,
        'action': action,
        'target_resource': target_resource,
        'target_id': target_id,
        'changes': changes,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    security_logger.info(f"ADMIN_ACTION: {json.dumps(log_data)}")

def log_jwt_token_event(event_type, user_id=None, token_info=None):
    """Log de eventos relacionados con tokens JWT"""
    client_info = get_client_info()
    
    log_data = {
        'event': 'JWT_TOKEN_EVENT',
        'event_type': event_type,  # CREATED, REFRESHED, EXPIRED, INVALID
        'user_id': user_id,
        'token_info': token_info,
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'client_info': client_info
    }
    
    if event_type in ['EXPIRED', 'INVALID']:
        security_logger.warning(f"JWT_TOKEN_EVENT: {json.dumps(log_data)}")
    else:
        security_logger.info(f"JWT_TOKEN_EVENT: {json.dumps(log_data)}")
