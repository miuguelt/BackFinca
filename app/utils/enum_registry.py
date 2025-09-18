"""
Registro y optimización de enumeradores para serialización JSON.
Este módulo centraliza la gestión de enums para garantizar una
serialización JSON consistente en toda la aplicación.
"""

import enum
import logging
from typing import Dict, Type, Set, Any, Optional
import json

logger = logging.getLogger(__name__)

class EnumRegistry:
    """
    Registro centralizado de enumeradores (enums) para serialización JSON.
    """
    
    # Registro de clases enum
    _registered_enums: Dict[str, Type[enum.Enum]] = {}
    
    @classmethod
    def register(cls, enum_class: Type[enum.Enum]) -> None:
        """
        Registra un enum para serialización JSON optimizada.
        
        Args:
            enum_class: La clase enum a registrar
        """
        if not issubclass(enum_class, enum.Enum):
            raise TypeError(f"{enum_class.__name__} no es un enum válido")
            
        # Registrar por nombre cualificado (módulo.clase)
        qualified_name = f"{enum_class.__module__}.{enum_class.__name__}"
        cls._registered_enums[qualified_name] = enum_class
        
        # También registrar por nombre simple para búsquedas más sencillas
        cls._registered_enums[enum_class.__name__] = enum_class
        
        logger.debug(f"Enum registrado para JSON: {qualified_name}")
    
    @classmethod

    def get_all_enums(cls) -> Dict[str, Type[enum.Enum]]:
        """
        Obtiene todos los enums registrados.
        
        Returns:
            Diccionario de nombre a clase enum
        """
        return cls._registered_enums
    
    @classmethod
    def get_enum(cls, name: str) -> Optional[Type[enum.Enum]]:
        """
        Obtiene un enum por nombre.
        
        Args:
            name: Nombre simple o cualificado del enum
            
        Returns:
            Clase enum o None si no se encuentra
        """
        return cls._registered_enums.get(name)
    
    @classmethod
    def is_enum(cls, obj: Any) -> bool:
        """
        Verifica si un objeto es una instancia de un enum registrado.
        
        Args:
            obj: Objeto a verificar
            
        Returns:
            True si es una instancia de enum registrado, False en otro caso
        """
        if isinstance(obj, enum.Enum):
            return True
            
        for enum_class in cls._registered_enums.values():
            if isinstance(obj, enum_class):
                return True
                
        return False
    
    @classmethod
    def serialize_enum(cls, enum_instance: enum.Enum) -> Any:
        """
        Serializa una instancia de enum a un valor JSON compatible.
        
        Args:
            enum_instance: Instancia de enum a serializar
            
        Returns:
            Valor serializado (normalmente string o número)
        """
        if not isinstance(enum_instance, enum.Enum):
            raise TypeError(f"{enum_instance} no es una instancia de enum")
            
        # Usar to_json si está disponible
        if hasattr(enum_instance, 'to_json') and callable(getattr(enum_instance, 'to_json')):
            return enum_instance.to_json()
            
        # De lo contrario, usar el valor
        return enum_instance.value
        
    @classmethod
    def enum_aware_encoder(cls, obj):
        """
        Función de default para JSONEncoder que maneja enums registrados.
        
        Args:
            obj: Objeto a serializar
            
        Returns:
            Representación serializable o levanta TypeError
        """
        if cls.is_enum(obj):
            return cls.serialize_enum(obj)
            
        # Deja que el encoder estándar maneje otros tipos
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        

class EnumJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder con soporte para enums registrados y tipos especiales como Decimal.
    """
    
    def default(self, obj):
        try:
            # Primero intentar con el registro de enums
            return EnumRegistry.enum_aware_encoder(obj)
        except TypeError:
            # Manejar tipos especiales
            import decimal
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            # Delegar a la implementación base para otros tipos
            return super().default(obj)


# Función de ayuda para registrar todos los enums predefinidos de la aplicación
def register_application_enums():
    """Registra automáticamente todos los enums conocidos de la aplicación"""
    from app.models.user import Role
    from app.models.animals import Sex, AnimalStatus
    from app.models.vaccines import VaccineType
    from app.models.control import HealthStatus
    from app.models.fields import LandStatus
    
    # Registrar cada enum
    EnumRegistry.register(Role)
    EnumRegistry.register(Sex)
    EnumRegistry.register(AnimalStatus)
    EnumRegistry.register(VaccineType)
    EnumRegistry.register(HealthStatus)
    EnumRegistry.register(LandStatus)
    
    logger.info(f"Se registraron {len(EnumRegistry.get_all_enums())} enums para serialización JSON")
