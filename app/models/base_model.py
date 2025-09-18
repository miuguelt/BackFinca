from app import db
from datetime import datetime
from sqlalchemy import inspect, or_, and_, desc, asc
from sqlalchemy.orm import selectinload, joinedload
import logging
import enum as _enum

logger = logging.getLogger(__name__)


# Excepción simple para validaciones internas
class ValidationError(Exception):
    def __init__(self, message, code="validation_error", field=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field

class BaseModel(db.Model):
    """Clase base optimizada para modelos con funcionalidades de namespace.

    Mejoras recientes:
    - Método unificado to_json() para serialización consistente.
    - Conversión explícita de enums a sus valores (evita dependencias implícitas del encoder).
    - Eliminación de métodos duplicados (delete) y código redundante.
    - Normalización y validación de datos centralizada en `_validate_and_normalize`.
    """

    __abstract__ = True

    # Campos comunes para todos los modelos
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    # Configuraciones por defecto para namespaces (pueden ser sobreescritas en subclases)
    _namespace_fields = []
    _namespace_relations = {}
    _searchable_fields = []
    _filterable_fields = []
    _sortable_fields = []
    _required_fields = []
    _unique_fields = []
    _enum_fields = {}

    @classmethod
    def _validate_and_normalize(cls, data, is_update=False, instance_id=None):
        """
        Valida y normaliza los datos del payload. Centraliza la lógica de requeridos,
        únicos y enums.
        """
        errors = []
        # 1. Normalizar y validar enums
        for field, enum_class in cls._enum_fields.items():
            if field in data and data[field] is not None:
                raw_value = data[field]
                if isinstance(raw_value, dict) and 'value' in raw_value:
                    raw_value = raw_value['value']
                
                if isinstance(raw_value, enum_class):
                    data[field] = raw_value # Ya es una instancia, no necesita más validación
                    continue

                try:
                    # Convertir string a instancia de enum
                    data[field] = enum_class(raw_value)
                except (ValueError, TypeError):
                    valid_values = [e.value for e in enum_class]
                    errors.append(f"El campo '{field}' debe ser uno de: {', '.join(valid_values)}")

        # 2. Validar campos requeridos (solo en creación)
        if not is_update:
            for field in cls._required_fields:
                if data.get(field) is None or (isinstance(data.get(field), str) and not data.get(field)):
                    errors.append(f"El campo '{field}' es requerido")

        # 3. Validar campos únicos
        for field in cls._unique_fields:
            if field in data and data[field] is not None:
                query = cls.query.filter(getattr(cls, field) == data[field])
                if is_update and instance_id:
                    query = query.filter(cls.id != instance_id)
                
                if query.first():
                    errors.append(f"El valor '{data[field]}' ya existe para el campo '{field}'")

        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")
        
        return data

    def to_namespace_dict(self, include_relations=False, depth=1, fields=None):
        """
        Serializa el modelo a un dict listo para respuesta JSON.
        Delega la serialización de valores al JSONEncoder centralizado.
        """
        from app.utils.json_utils import JSONEncoder

        target_fields = fields or self._namespace_fields
        data = {field: JSONEncoder.serialize(getattr(self, field, None)) for field in target_fields}

        # Relaciones (solo si se solicita y depth>0)
        if include_relations and depth > 0:
            for rel_name, cfg in self._namespace_relations.items():
                if hasattr(self, rel_name):
                    rel_obj = getattr(self, rel_name)
                    rel_fields = cfg.get('fields')
                    
                    try:
                        if rel_obj is None:
                            data[rel_name] = None
                        elif hasattr(rel_obj, 'all'):  # Relación dinámica (lazy='dynamic')
                            data[rel_name] = [
                                item.to_namespace_dict(include_relations=False, depth=depth-1, fields=rel_fields)
                                for item in rel_obj.limit(50)  # Límite defensivo
                            ]
                        elif isinstance(rel_obj, list):
                            data[rel_name] = [
                                item.to_namespace_dict(include_relations=False, depth=depth-1, fields=rel_fields)
                                for item in rel_obj
                            ]
                        else: # Relación a un solo objeto
                            data[rel_name] = rel_obj.to_namespace_dict(
                                include_relations=False, depth=depth-1, fields=rel_fields
                            )
                    except Exception as e:
                        logger.debug(f"Error serializando relación {rel_name} en {self.__class__.__name__}: {e}")
                        data[rel_name] = None
        return data

    # Alias explícito usado por algunos serializadores
    def to_json(self):  # pragma: no cover - simple delegación
        return self.to_namespace_dict()

    @classmethod
    def get_namespace_query(cls, filters=None, search=None, sort_by=None, sort_order='asc',
                           page=None, per_page=None, include_relations=False):  # per_page retained for backward compat
        """Construir consulta optimizada para namespaces"""
        query = cls.query

        # Eager load de relaciones si se solicitan (evita N+1 en listados)
        if include_relations:
            try:
                for relation_name in cls._namespace_relations.keys():
                    if hasattr(cls, relation_name):
                        query = query.options(selectinload(getattr(cls, relation_name)))
            except Exception:
                # Fallback silencioso si el backend de ORM no soporta la opción
                pass

        # Aplicar filtros
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if key in cls._filterable_fields and hasattr(cls, key):
                    if isinstance(value, list):
                        filter_conditions.append(getattr(cls, key).in_(value))
                    else:
                        filter_conditions.append(getattr(cls, key) == value)

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        # Aplicar búsqueda
        if search and cls._searchable_fields:
            search_conditions = []
            for field in cls._searchable_fields:
                if hasattr(cls, field):
                    search_conditions.append(getattr(cls, field).ilike(f'%{search}%'))

            if search_conditions:
                query = query.filter(or_(*search_conditions))

        # Aplicar ordenamiento
        if sort_by and sort_by in cls._sortable_fields and hasattr(cls, sort_by):
            order_func = asc if sort_order.lower() == 'asc' else desc
            query = query.order_by(order_func(getattr(cls, sort_by)))
        else:
            # Orden por defecto
            query = query.order_by(desc(cls.created_at))

        # Aplicar paginación
        if page and per_page:
            # Mantener parámetro per_page para compatibilidad; namespace_helpers ya pasa 'limit' mapeado aquí
            query = query.paginate(page=page, per_page=per_page, error_out=False)

        return query

    @classmethod
    def get_paginated_response(cls, query_result, include_relations=False, depth=1):
        """Convertir resultado paginado a respuesta de namespace"""
        if hasattr(query_result, 'items'):
            # Es un resultado paginado
            items = [item.to_namespace_dict(include_relations=include_relations, depth=depth)
                    for item in query_result.items]
            # Return both legacy keys and the new unified pagination keys to preserve
            # backward compatibility across the codebase while enabling the
            # namespace layer to consume the canonical contract.
            return {
                'items': items,
                # legacy keys
                'total': query_result.total,
                'page': query_result.page,
                'per_page': query_result.per_page,
                'pages': query_result.pages,
                'has_next': query_result.has_next,
                'has_prev': query_result.has_prev,
                # new unified keys
                'total_items': query_result.total,
                'limit': query_result.per_page,
                'total_pages': query_result.pages,
                'has_next_page': query_result.has_next,
                'has_previous_page': query_result.has_prev,
            }
        else:
            # Es una lista simple
            items = [item.to_namespace_dict(include_relations=include_relations, depth=depth)
                    for item in query_result]
            # For non-paginated lists, return a compatible structure with both
            # legacy and new pagination keys.
            return {
                'items': items,
                # legacy keys
                'total': len(items),
                'page': 1,
                'per_page': len(items),
                'pages': 1,
                'has_next': False,
                'has_prev': False,
                # new unified keys
                'total_items': len(items),
                'limit': len(items),
                'total_pages': 1,
                'has_next_page': False,
                'has_previous_page': False,
            }

    @classmethod
    def bulk_create(cls, items_data):
        """Crear múltiples instancias de forma optimizada."""
        instances = [cls(**cls._validate_and_normalize(data)) for data in items_data]
        db.session.add_all(instances)
        db.session.commit()
        return instances

    @classmethod
    def bulk_update(cls, updates_data):
        """Actualizar múltiples instancias de forma optimizada."""
        updated_instances = []
        for update_data in updates_data:
            instance_id = update_data.get('id')
            if not instance_id:
                raise ValidationError("ID requerido para actualización masiva", code="missing_id")

            instance = db.session.get(cls, instance_id)
            if not instance:
                raise ValidationError(f"Instancia con ID {instance_id} no encontrada", code="not_found")

            data_to_update = {k: v for k, v in update_data.items() if k != 'id'}
            normalized_data = cls._validate_and_normalize(data_to_update, is_update=True, instance_id=instance_id)
            
            for key, value in normalized_data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            updated_instances.append(instance)

        db.session.commit()
        return updated_instances


    def save(self):
        """Persistir cambios en DB con actualización de timestamp."""
        from datetime import datetime, timezone
        try:
            self.updated_at = datetime.now(timezone.utc)
        except Exception:
            pass
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self, commit=True):  # Mantener solo UNA definición de delete
        """Eliminar instancia de la base de datos."""
        db.session.delete(self)
        if commit:
            db.session.commit()
        return True


    @classmethod
    def get_or_create(cls, **kwargs):
        instance = cls.query.filter_by(**kwargs).first()
        if instance:
            return instance, False
        instance = cls(**kwargs)
        instance.save()
        return instance, True

    @classmethod
    def exists(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first() is not None


    def refresh(self):
        db.session.refresh(self)
        return self


    @property
    def is_new(self):
        return inspect(self).transient

    @classmethod
    def get_by_id(cls, record_id, include_relations=False):
        """Obtener instancia por ID con opción de incluir relaciones."""
        query = cls.query
        if include_relations:
            for relation_name in cls._namespace_relations.keys():
                if hasattr(cls, relation_name):
                    query = query.options(selectinload(getattr(cls, relation_name)))
        
        return query.filter_by(id=record_id).first()

    @classmethod
    def create(cls, **kwargs):
        """Crear nueva instancia con validación y normalización."""
        normalized_data = cls._validate_and_normalize(kwargs, is_update=False)
        from datetime import datetime
        from app import db  # Asegurar acceso a timezone si está configurada
        normalized_data['created_at'] = datetime.utcnow()
        normalized_data['updated_at'] = datetime.utcnow()
        instance = cls(**normalized_data)
        instance.save()
        return instance

    def update(self, commit=True, **kwargs):
        """Actualizar instancia con validación y normalización."""
        normalized_data = self.__class__._validate_and_normalize(kwargs, is_update=True, instance_id=self.id)
        
        for key, value in normalized_data.items():
            if hasattr(self, key):
                setattr(self, key, value)

        if commit:
            self.save()
        return self

    # (El método delete duplicado fue eliminado para evitar confusión)

    @classmethod
    def get_all(cls, include_relations=False):
        """Obtener todas las instancias"""
        if include_relations:
            query = cls.query
            for relation_name in cls._namespace_relations.keys():
                if hasattr(cls, relation_name):
                    query = query.options(selectinload(getattr(cls, relation_name)))
            return query.all()
        else:
            return cls.query.all()

    @classmethod
    def get_filtered(cls, **filters):
        """Obtener instancias filtradas"""
        return cls.query.filter_by(**filters).all()

    @classmethod
    def count(cls, **filters):
        """Contar instancias con filtros opcionales"""
        if filters:
            return cls.query.filter_by(**filters).count()
        return cls.query.count()

    @classmethod
    def exists_by_field(cls, field_name, value):
        """Verificar si existe instancia con valor específico en campo"""
        return cls.query.filter(getattr(cls, field_name) == value).first() is not None

    def to_namespace_dict_with_relations(self, depth=1):
        """Serialización con relaciones incluidas"""
        return self.to_namespace_dict(include_relations=True, depth=depth)

    @classmethod
    def search(cls, search_term, fields=None, limit=50):
        """Búsqueda simple en campos especificados"""
        if not fields:
            fields = cls._searchable_fields

        if not fields:
            return []

        search_filters = []
        for field in fields:
            if hasattr(cls, field):
                search_filters.append(getattr(cls, field).ilike(f'%{search_term}%'))


        if search_filters:
            return cls.query.filter(or_(*search_filters)).limit(limit).all()

        return []

    @classmethod
    def get_recent(cls, limit=10, include_relations=False):
        """Obtener registros más recientes"""
        query = cls.query.order_by(cls.created_at.desc()).limit(limit)

        if include_relations:
            for relation_name in cls._namespace_relations.keys():
                if hasattr(cls, relation_name):
                    query = query.options(selectinload(getattr(cls, relation_name)))

        return query.all()

    def duplicate(self):
        """Crear duplicado de la instancia (sin ID)"""
        data = self.to_namespace_dict()
        data.pop('id', None)
        data.pop('created_at', None)
        data.pop('updated_at', None)
        return self.__class__(**data)

    @classmethod
    def bulk_delete(cls, ids):
        """Eliminar múltiples instancias por IDs"""
        cls.query.filter(cls.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return len(ids)

    @classmethod
    def get_stats(cls):
        """Obtener estadísticas básicas del modelo"""
        total_count = cls.count()
        from datetime import datetime, timezone
        recent_count = cls.query.filter(
            cls.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()

        return {
            'total': total_count,
            'recent_today': recent_count,
            'model_name': cls.__name__
        }
