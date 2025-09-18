"""
Validadores mejorados para la aplicación con seguridad reforzada
"""

import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional
import unicodedata
import logging
from functools import wraps
from flask import request, g
from flask_jwt_extended import get_jwt_identity, get_jwt
import time

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    def __init__(self, message: str, field: str = None, code: str = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code or 'validation_error'

class SecurityValidator:
    """Validador de seguridad para detectar patrones maliciosos"""
    
    # Patrones sospechosos comunes
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|;|\||\|\||&&)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT)\b)",
        r"(<\s*script\b)",
        r"(javascript\s*:)",
        r"(\bEXEC\s*\()",
        r"(\bSP_)",
        r"(\bXP_)"
    ]
    
    XSS_PATTERNS = [
        r"(<\s*script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>)",
        r"(<\s*iframe\b)",
        r"(<\s*object\b)",
        r"(<\s*embed\b)",
        r"(<\s*link\b)",
        r"(<\s*meta\b)",
        r"(javascript\s*:)",
        r"(vbscript\s*:)",
        r"(on\w+\s*=)",
        r"(\beval\s*\()",
        r"(\balert\s*\()",
        r"(\bconfirm\s*\()",
        r"(\bprompt\s*\()"
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.\/)",
        r"(\.\.\\)",
        r"(%2e%2e%2f)",
        r"(%2e%2e%5c)",
        r"(\.\.%2f)",
        r"(\.\.%5c)"
    ]

    @classmethod
    def check_malicious_content(cls, value: str, field_name: str = "campo") -> None:
        """Verificar contenido malicioso en entrada de usuario"""
        if not isinstance(value, str):
            return
        
        value_lower = value.lower()
        
        # Verificar SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"Posible SQL injection detectado en {field_name}: {value[:100]}")
                raise ValidationError(
                    f"Contenido no permitido detectado en {field_name}",
                    field=field_name,
                    code="malicious_content"
                )
        
        # Verificar XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Posible XSS detectado en {field_name}: {value[:100]}")
                raise ValidationError(
                    f"Contenido no permitido detectado en {field_name}",
                    field=field_name,
                    code="malicious_content"
                )
        
        # Verificar path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Posible path traversal detectado en {field_name}: {value[:100]}")
                raise ValidationError(
                    f"Contenido no permitido detectado en {field_name}",
                    field=field_name,
                    code="malicious_content"
                )
    
    @staticmethod
    def require_admin_role(f):
        """Decorator que requiere rol de Administrador"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                user_id = get_jwt_identity()
                user_claims = get_jwt()
                token_role = user_claims.get('role') if user_claims else None

                # Revalidar rol contra la base de datos para evitar privilegios desactualizados
                db_role = None
                current_status = None
                if user_id:
                    try:
                        from app.models.user import User  # Import local para evitar ciclos
                        user_obj = User.get_by_id(user_id)
                        if user_obj:
                            db_role = user_obj.role.value if user_obj.role else None
                            current_status = user_obj.status
                    except Exception as db_err:
                        logger.debug(f"No se pudo cargar usuario para validación de rol admin: {db_err}")

                effective_role = db_role or token_role
                if not user_id or effective_role != 'Administrador' or current_status is False:
                    from app.utils.response_handler import APIResponse
                    # Mensaje uniforme pero con detalles opcionales para diagnosticar en front si se requiere
                    return APIResponse.forbidden(
                        "Se requiere rol de Administrador para esta operación",
                        details={
                            'token_role': token_role,
                            'db_role': db_role,
                            'user_status': current_status
                        }
                    )
            except Exception:
                from app.utils.response_handler import APIResponse
                return APIResponse.unauthorized("Token JWT inválido")
            
            return f(*args, **kwargs)
        return decorated_function

def sanitize_string(value: str, max_length: int = None) -> str:
    """Limpiar y sanitizar string de entrada"""
    if not isinstance(value, str):
        return str(value)
    
    # Normalizar unicode
    value = unicodedata.normalize('NFKC', value)
    
    # Remover caracteres de control
    value = ''.join(char for char in value if not unicodedata.category(char).startswith('C'))
    
    # Limpiar espacios
    value = ' '.join(value.split())
    
    # Aplicar longitud máxima si se especifica
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value

def validate_email(email: str, field_name: str = "email") -> str:
    """Validar formato de email con sanitización"""
    if not email:
        raise ValidationError(f"{field_name} es requerido", field=field_name)
    
    email = sanitize_string(email, 254)  # RFC 5321 limit
    
    # Verificar seguridad
    SecurityValidator.check_malicious_content(email, field_name)
    
    # Patrón de email más estricto
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValidationError(
            f"{field_name} debe tener un formato válido",
            field=field_name,
            code="invalid_format"
        )
    
    # Verificar longitud de partes
    local_part, domain = email.split('@')
    if len(local_part) > 64:  # RFC 5321 limit
        raise ValidationError(
            f"{field_name} demasiado largo",
            field=field_name,
            code="too_long"
        )
    
    return email.lower()

def validate_phone(phone: str, field_name: str = "teléfono") -> str:
    """Validar número de teléfono"""
    if not phone:
        raise ValidationError(f"{field_name} es requerido", field=field_name)
    
    phone = sanitize_string(phone, 20)
    
    # Verificar seguridad
    SecurityValidator.check_malicious_content(phone, field_name)
    
    # Limpiar caracteres no numéricos excepto + y espacios
    clean_phone = re.sub(r'[^\d\+\s\-\(\)]', '', phone)
    
    # Patrón para teléfono (colombiano principalmente)
    phone_pattern = r'^(\+57\s?)?[0-9\s\-\(\)]{7,15}$'
    
    if not re.match(phone_pattern, clean_phone):
        raise ValidationError(
            f"{field_name} debe tener un formato válido",
            field=field_name,
            code="invalid_format"
        )
    
    return clean_phone

def validate_identification(identification: Any, field_name: str = "identificación") -> int:
    """Validar número de identificación"""
    if identification is None:
        raise ValidationError(f"{field_name} es requerido", field=field_name)
    
    try:
        identification = int(identification)
    except (ValueError, TypeError):
        raise ValidationError(
            f"{field_name} debe ser un número",
            field=field_name,
            code="invalid_type"
        )
    
    if identification <= 0:
        raise ValidationError(
            f"{field_name} debe ser un número positivo",
            field=field_name,
            code="invalid_range"
        )
    
    if identification > 9999999999:  # 10 dígitos máximo
        raise ValidationError(
            f"{field_name} es demasiado largo",
            field=field_name,
            code="too_long"
        )
    
    return identification

def validate_password(password: str, field_name: str = "contraseña") -> None:
    """Validar fortaleza de contraseña"""
    if not password:
        raise ValidationError(f"{field_name} es requerida", field=field_name)
    
    # Verificar longitud
    if len(password) < 8:
        raise ValidationError(
            f"{field_name} debe tener al menos 8 caracteres",
            field=field_name,
            code="too_short"
        )
    
    if len(password) > 128:
        raise ValidationError(
            f"{field_name} es demasiado larga",
            field=field_name,
            code="too_long"
        )
    
    # Verificar complejidad básica
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if sum([has_upper, has_lower, has_digit, has_special]) < 3:
        raise ValidationError(
            f"{field_name} debe contener al menos 3 de: mayúscula, minúscula, número, símbolo",
            field=field_name,
            code="weak_password"
        )

class RequestValidator:
    """Sistema de validaciones automáticas para endpoints"""
    
    @staticmethod
    def validate_json_required(f):
        """Decorator que valida que la petición tenga JSON válido"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                from app.utils.response_handler import APIResponse
                return APIResponse.validation_error(
                    {"content_type": "Se requiere Content-Type: application/json"},
                    "Formato de petición inválido"
                )
            
            try:
                data = request.get_json()
                # Validar tamaño de request
                if isinstance(data, dict):
                    validate_request_size(data)
            except Exception as e:
                from app.utils.response_handler import APIResponse
                return APIResponse.validation_error(
                    {"json": f"JSON inválido: {str(e)}"},
                    "Error de formato JSON"
                )
            
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def validate_fields(required_fields: List[str] = None, 
                       optional_fields: List[str] = None,
                       field_types: Dict[str, type] = None):
        """Decorator que valida campos requeridos y tipos de datos"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                data = request.get_json() or {}
                errors = {}
                
                # Validar campos requeridos
                if required_fields:
                    for field in required_fields:
                        if field not in data or data[field] is None:
                            errors[field] = f"Campo '{field}' es requerido"
                        elif isinstance(data[field], str) and not data[field].strip():
                            errors[field] = f"Campo '{field}' no puede estar vacío"
                
                # Validar tipos de datos
                if field_types:
                    for field, expected_type in field_types.items():
                        if field in data and data[field] is not None:
                            if not isinstance(data[field], expected_type):
                                errors[field] = f"Campo '{field}' debe ser de tipo {expected_type.__name__}"
                
                # Validar campos no permitidos
                allowed_fields = set((required_fields or []) + (optional_fields or []))
                if allowed_fields:
                    for field in data.keys():
                        if field not in allowed_fields:
                            errors[field] = f"Campo '{field}' no está permitido"
                
                if errors:
                    from app.utils.response_handler import APIResponse
                    return APIResponse.validation_error(errors)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

def validate_request_size(data: Dict[str, Any], max_fields: int = 50) -> None:
    """Validar tamaño de request para prevenir DoS"""
    if len(data) > max_fields:
        raise ValidationError(
            f"Demasiados campos en la solicitud (máximo {max_fields})",
            code="request_too_large"
        )
    
    # Verificar tamaño total de strings
    total_string_length = 0
    for key, value in data.items():
        if isinstance(value, str):
            total_string_length += len(value)
        if total_string_length > 100000:  # 100KB de strings
            raise ValidationError(
                "Solicitud demasiado grande",
                code="request_too_large"
            )

class PerformanceLogger:
    """Sistema de logging de rendimiento y métricas"""
    
    @staticmethod
    def log_request_performance(f):
        """Decorator que registra métricas de rendimiento de requests"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Información de la petición
            user_info = "Anonymous"
            try:
                jwt_identity = get_jwt_identity()
                if jwt_identity:
                    user_info = f"User {jwt_identity}"
            except:
                pass
            
            logger.info(
                f"REQUEST START: {request.method} {request.path} | "
                f"User: {user_info} | IP: {request.remote_addr}"
            )
            
            try:
                # Ejecutar función
                result = f(*args, **kwargs)
                
                # Calcular tiempo de respuesta
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)  # en ms
                
                # Determinar código de estado
                status_code = 200
                if isinstance(result, tuple) and len(result) > 1:
                    status_code = result[1]
                
                logger.info(
                    f"REQUEST END: {request.method} {request.path} | "
                    f"Status: {status_code} | Time: {response_time}ms | User: {user_info}"
                )
                
                # Alertar sobre requests lentos
                if response_time > 1000:  # > 1 segundo
                    logger.warning(
                        f"SLOW REQUEST: {request.method} {request.path} | "
                        f"Time: {response_time}ms | User: {user_info}"
                    )
                
                return result
                
            except Exception as e:
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)
                
                logger.error(
                    f"REQUEST ERROR: {request.method} {request.path} | "
                    f"Error: {str(e)} | Time: {response_time}ms | User: {user_info}"
                )
                raise
        
        return decorated_function