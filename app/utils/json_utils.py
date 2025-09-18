"""
Utilidades avanzadas para optimizar el manejo de JSON en toda la aplicación.
Proporciona funciones para serialización consistente y eficiente.
"""

from datetime import datetime, date, time, timezone
from enum import Enum
import decimal
import uuid
from typing import Any, Dict, List, Union, Set, Optional
import logging
import enum

logger = logging.getLogger(__name__)

class JSONEncoder:
    """
    Codificador JSON optimizado con soporte para tipos adicionales.
    Reemplaza el jsonify predeterminado de Flask con una versión más eficiente.
    """
    
    @staticmethod
    def serialize(obj: Any) -> Any:
        """
        Serializa un objeto para JSON, manejando tipos especiales.
        
        Args:
            obj: El objeto a serializar
            
        Returns:
            Una versión serializable del objeto
        """
        try:
            # None pasa directo
            if obj is None:
                return None
                
            # Tipos básicos que no necesitan conversión
            if isinstance(obj, (str, int, float, bool)):
                return obj
                
            # Fechas y horas -> ISO8601
            if isinstance(obj, datetime):
                # Normalizar al formato JSON preferido: ISO-8601 con 'Z' para UTC
                if obj.tzinfo is not None:
                    return obj.isoformat().replace('+00:00', 'Z')
                # Sin timezone, asumir UTC
                return obj.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
            
            if isinstance(obj, date):
                return obj.isoformat()
                
            if isinstance(obj, time):
                return obj.isoformat()
            
            # Decimal -> float con precisión (para JSON)
            if isinstance(obj, decimal.Decimal):
                # Convertir Decimal a float para serialización JSON
                return float(obj)
            
            # UUID -> string
            if isinstance(obj, uuid.UUID):
                return str(obj)
                
            # Usar el registro de enums para serialización consistente
            try:
                from app.utils.enum_registry import EnumRegistry
                if EnumRegistry.is_enum(obj):
                    return EnumRegistry.serialize_enum(obj)
            except ImportError:
                pass
                
            # Enum -> valor (fallback general si no está registrado)
            if isinstance(obj, Enum):
                return obj.value
                
            # Diccionarios -> procesar valores recursivamente
            if isinstance(obj, dict):
                return {k: JSONEncoder.serialize(v) for k, v in obj.items()}
            
            # Listas, tuplas, sets -> procesar elementos recursivamente
            if isinstance(obj, (list, tuple, set)):
                return [JSONEncoder.serialize(item) for item in obj]
            
            # SQLAlchemy models con to_dict/to_json
            if hasattr(obj, 'to_json'):
                return JSONEncoder.serialize(obj.to_json())
                
            if hasattr(obj, 'to_dict'):
                return JSONEncoder.serialize(obj.to_dict())
                
            if hasattr(obj, 'to_namespace_dict'):
                return JSONEncoder.serialize(obj.to_namespace_dict())
            
            # SQLAlchemy models sin métodos pero con __table__
            if hasattr(obj, '__table__'):
                from sqlalchemy import inspect
                return JSONEncoder.serialize({c.name: getattr(obj, c.name) 
                        for c in inspect(obj.__class__).columns})
            
            # Bytearrays/bytes -> str base64
            if isinstance(obj, (bytearray, bytes)):
                import base64
                return base64.b64encode(obj).decode('utf-8')
            
            # Objetos con __dict__ (como dataclass)
            if hasattr(obj, '__dict__'):
                return JSONEncoder.serialize(obj.__dict__)
                
            # Cualquier otro objeto -> str()
            return str(obj)
            
        except Exception as e:
            logger.warning(f"Error serializando objeto {type(obj)}: {e}")
            return str(obj)

    @classmethod
    def sanitize_object(cls, data: Any) -> Any:
        """
        Sanitiza un objeto completo para asegurar que es JSON-serializable.
        
        Args:
            data: El objeto a sanitizar
            
        Returns:
            Una versión completamente serializable del objeto
        """
        return cls.serialize(data)

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Convierte un objeto a JSON de manera segura con el encoder optimizado.
    
    Args:
        obj: El objeto a serializar
        **kwargs: Argumentos adicionales para json.dumps
        
    Returns:
        String JSON
    """
    import json
    import enum
    
    # Usar el encoder de EnumRegistry si está disponible
    try:
        from app.utils.enum_registry import EnumJSONEncoder
        encoder_cls = EnumJSONEncoder
    except ImportError:
        # Encoder de fallback si no está disponible EnumRegistry
        class FallbackJSONEncoder(json.JSONEncoder):
            def default(self, o):
                # Manejar tipos especiales
                if isinstance(o, enum.Enum):
                    return o.value
                # Manejar cualquier otro objeto con nuestro serializador
                return JSONEncoder.serialize(o)
        encoder_cls = FallbackJSONEncoder
    
    try:
        # Primero aplicar nuestro sanitizador
        sanitized = JSONEncoder.sanitize_object(obj)
        # Luego usar un encoder personalizado para el dumps
        return json.dumps(sanitized, ensure_ascii=False, cls=encoder_cls, **kwargs)
    except Exception as e:
        logger.error(f"Error en safe_json_dumps: {e}", exc_info=True)
        return json.dumps({"error": "Error serializando objeto", "details": str(e)})
