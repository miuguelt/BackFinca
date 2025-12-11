from flask import jsonify, request, current_app
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union
from app.utils.json_utils import JSONEncoder
import uuid

logger = logging.getLogger(__name__)

def _current_access_token() -> Optional[str]:
    """Extrae el access_token de la solicitud actual, ya sea del header Authorization o de la cookie HttpOnly.
    - Authorization: "Bearer <token>"
    - Cookie: access_token_cookie
    Devuelve None si no está presente.
    """
    try:
        # Prioridad: Authorization header
        auth = request.headers.get('Authorization', '') if request else ''
        if isinstance(auth, str) and auth.lower().startswith('bearer '):
            return auth.split(' ', 1)[1].strip()
        # Fallback: cookie HttpOnly usada por Flask-JWT-Extended
        if request and request.cookies:
            cookie_name = (current_app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token_cookie')
                           if current_app else 'access_token_cookie')
            cookie_token = request.cookies.get(cookie_name)
            if cookie_token:
                return cookie_token
    except Exception:
        # No bloquear la respuesta por fallos menores al extraer el token
        pass
    return None

class APIResponse:
    """
    Sistema de respuestas estandarizadas para compatibilidad total con React.
    Proporciona estructura consistente y códigos de estado HTTP apropiados.
    """
    
    @staticmethod
    def success(data: Any = None, message: str = "Operación exitosa",
                status_code: int = 200, meta: Optional[Dict] = None,
                include_token: bool = False) -> tuple:
        """
        Respuesta de éxito estandarizada.

        Args:
            data: Datos a retornar (puede ser dict, list, etc.)
            message: Mensaje descriptivo
            status_code: Código HTTP (200, 201, etc.)
            meta: Metadatos adicionales (paginación, totales, etc.)
            include_token: Si True, incluye el access_token en la respuesta (solo para auth)

        Returns:
            Tuple con (response_json, status_code)
        """
        # Estructura base de éxito
        response = {
            "success": True,
            "data": data,
            "message": message,
        }

        # Compatibilidad con endpoints de auth:
        # si los datos incluyen un access_token, refléjalo también en la raíz.
        if isinstance(data, dict) and "access_token" in data:
            response["access_token"] = data.get("access_token")

        # Mantener include_token como fallback (por ejemplo, para /auth/me si se usa).
        if include_token and "access_token" not in response:
            token = _current_access_token()
            if token:
                response["access_token"] = token

        if meta:
            response["meta"] = meta

        logger.info(f"Success response: {status_code} - {message}")
        return response, status_code
    
    @staticmethod
    def error(message: str, status_code: int = 400,
              error_code: Optional[str] = None,
              details: Optional[Dict] = None) -> tuple:
        """
        Respuesta de error estandarizada.

        Args:
            message: Mensaje de error descriptivo
            status_code: Código HTTP de error
            error_code: Código interno de error (opcional)
            details: Detalles adicionales del error

        Returns:
            Tuple con (response_json, status_code)
        """
        trace_id = str(uuid.uuid4())
        logger.error(f"Error response: {status_code} - {message} (Trace ID: {trace_id})")

        response = {
            "success": False,
            # Incluir mensaje en la raíz para que el frontend lo pueda mostrar en alertas genéricas
            "message": message,
            "error": {
                "code": error_code or f"HTTP_{status_code}",
                "message": message,
                "details": details or {},
                "trace_id": trace_id
            }
        }

        return response, status_code
    
    @staticmethod
    def validation_error(errors: Union[Dict, List], 
                        message: str = "Errores de validación",
                        status_code: int = 422) -> tuple:
        """
        Respuesta específica para errores de validación.
        
        Args:
            errors: Errores de validación (dict o list)
            message: Mensaje principal
            status_code: Código HTTP a devolver (por defecto 422)
        
        Returns:
            Tuple con (response_json, status_code)
        """
        return APIResponse.error(
            message=message,
            status_code=status_code,
            error_code="VALIDATION_ERROR",
            details={"validation_errors": errors}
        )
    
    @staticmethod
    def not_found(resource: str = "Recurso") -> tuple:
        """
        Respuesta para recursos no encontrados.
        
        Args:
            resource: Nombre del recurso no encontrado
        
        Returns:
            Tuple con (response_json, 404)
        """
        return APIResponse.error(
            message=f"{resource} no encontrado",
            status_code=404,
            error_code="NOT_FOUND"
        )
    
    @staticmethod
    def unauthorized(message: str = "Acceso no autorizado") -> tuple:
        """
        Respuesta para errores de autenticación.
        
        Args:
            message: Mensaje de error personalizado
        
        Returns:
            Tuple con (response_json, 401)
        """
        return APIResponse.error(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED"
        )
    
    @staticmethod
    def forbidden(message: str = "Acceso prohibido") -> tuple:
        """
        Respuesta para errores de autorización.
        
        Args:
            message: Mensaje de error personalizado
        
        Returns:
            Tuple con (response_json, 403)
        """
        return APIResponse.error(
            message=message,
            status_code=403,
            error_code="FORBIDDEN"
        )
    
    @staticmethod
    def conflict(message: str = "Conflicto de datos", details: Optional[Dict] = None) -> tuple:
        """
        Respuesta para conflictos de integridad.
        
        Args:
            message: Mensaje de error
            details: Detalles del conflicto
        
        Returns:
            Tuple con (response_json, 409)
        """
        return APIResponse.error(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )
    
    @staticmethod
    def paginated_success(data: List, page: int, limit: int, 
                         total_items: int, message: str = "Datos obtenidos exitosamente") -> tuple:
        """
        Respuesta de éxito con paginación estandarizada.
        
        Args:
            data: Lista de datos
            page: Página actual
            limit: Elementos por página
            total_items: Total de elementos
            message: Mensaje descriptivo
        
        Returns:
            Tuple con (response_json, 200)
        """
        total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0
        
        meta = {
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next_page": page < total_pages,
                "has_previous_page": page > 1
            }
        }
        
        return APIResponse.success(
            data=data,
            message=message,
            meta=meta
        )
    
    @staticmethod
    def created(data: Any, message: str = "Recurso creado exitosamente") -> tuple:
        """
        Respuesta para recursos creados.
        
        Args:
            data: Datos del recurso creado
            message: Mensaje de éxito
        
        Returns:
            Tuple con (response_json, 201)
        """
        return APIResponse.success(
            data=data,
            message=message,
            status_code=201
        )
    
    @staticmethod
    def no_content(message: str = "Operación completada") -> tuple:
        """
        Respuesta sin contenido (para DELETE exitoso).
        
        Args:
            message: Mensaje de confirmación
        
        Returns:
            Tuple con (response_json, 200)
        """
        return APIResponse.success(
            data=None,
            message=message,
            status_code=200
        )


class ResponseFormatter:
    """
    Formateador de datos para respuestas consistentes.
    """
    
    @staticmethod
    def format_model(model_instance, exclude_fields: Optional[List[str]] = None) -> Dict:
        """
        Formatea una instancia de modelo SQLAlchemy.
        
        Args:
            model_instance: Instancia del modelo
            exclude_fields: Campos a excluir
        
        Returns:
            Diccionario con los datos formateados
        """
        if hasattr(model_instance, 'to_json'):
            data = model_instance.to_json()
        else:
            # Fallback para modelos sin to_json
            data = {c.name: getattr(model_instance, c.name) 
                   for c in model_instance.__table__.columns}
        
        if exclude_fields:
            for field in exclude_fields:
                data.pop(field, None)
        
        return data
    
    @staticmethod
    def format_model_list(model_list, exclude_fields: Optional[List[str]] = None) -> List[Dict]:
        """
        Formatea una lista de modelos SQLAlchemy.
        
        Args:
            model_list: Lista de instancias de modelo
            exclude_fields: Campos a excluir
        
        Returns:
            Lista de diccionarios formateados
        """
        return [ResponseFormatter.format_model(model, exclude_fields) 
                for model in model_list]
    
    @staticmethod
    def sanitize_for_frontend(data: Any) -> Any:
        """
        Sanitiza datos para el frontend usando el JSONEncoder optimizado.
        
        Args:
            data: Datos a sanitizar
        
        Returns:
            Datos sanitizados
        """
        from app.utils.json_utils import JSONEncoder
        return JSONEncoder.sanitize_object(data)
