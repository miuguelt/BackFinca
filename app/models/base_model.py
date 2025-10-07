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
    # Defaults en cliente y servidor para evitar errores en BD sin defaults
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,              # client-side default
        server_default=db.func.now(),         # server-side default
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,              # client-side default
        onupdate=datetime.utcnow,             # client-side onupdate
        server_default=db.func.now(),         # server-side default
        nullable=False
    )

    # Configuraciones por defecto para namespaces (pueden ser sobreescritas en subclases)
    _namespace_fields = []
    _namespace_relations = {}
    _searchable_fields = []
    _filterable_fields = []
    _sortable_fields = []
    _required_fields = []
    _unique_fields = []
    _enum_fields = {}

    # Configuración de caché para PWA (optimizado para diferentes tipos de datos)
    _cache_config = {
        'ttl': 120,  # TTL en segundos (2 minutos por defecto)
        'type': 'private',  # 'public' (compartido) o 'private' (por usuario)
        'strategy': 'stale-while-revalidate',  # estrategia para Service Worker
        'max_age': 120,  # max-age para Cache-Control header
        'stale_while_revalidate': 60,  # tiempo para usar caché stale mientras revalida
    }

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

        # Si no se especifican campos, usar todos los campos de la tabla
        if fields is None:
            # Si el modelo tiene _namespace_fields definido, usarlos
            if hasattr(self, '_namespace_fields') and self._namespace_fields:
                target_fields = self._namespace_fields
            else:
                # Si no, incluir automáticamente todos los campos de la tabla
                target_fields = [col.name for col in self.__table__.columns]
        else:
            target_fields = fields

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
    def get_namespace_query(cls, filters=None, search=None, search_type='auto', sort_by=None, sort_order='asc',
                           page=None, per_page=None, include_relations=False):  # per_page retained for backward compat
        """Construir consulta optimizada para namespaces"""
        query = cls.query

        # Eager load de relaciones si se solicitan (evita N+1 en listados)
        if include_relations:
            try:
                for relation_name in cls._namespace_relations.keys():
                    if hasattr(cls, relation_name):
                        # Verificar si la relación es dinámica antes de aplicar selectinload
                        relation_attr = getattr(cls, relation_name)
                        if hasattr(relation_attr.property, 'lazy') and relation_attr.property.lazy == 'dynamic':
                            continue  # Saltar relaciones dinámicas
                        query = query.options(selectinload(relation_attr))
            except Exception:
                # Fallback silencioso si el backend de ORM no soporta la opción
                pass

        # Aplicar filtros
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                # Filtro especial para delta sync (sincronización incremental)
                if key == '_since':
                    # Filtrar por updated_at >= since_date (registros modificados desde timestamp)
                    if hasattr(cls, 'updated_at'):
                        filter_conditions.append(cls.updated_at >= value)
                        logger.debug(f"Delta sync filter: {cls.__name__}.updated_at >= {value}")
                    continue

                if key in cls._filterable_fields and hasattr(cls, key):
                    if isinstance(value, list):
                        filter_conditions.append(getattr(cls, key).in_(value))
                        logger.debug(f"Filtro aplicado: {cls.__name__}.{key} IN {value} (tipo: {type(value[0]) if value else 'empty'})")
                    else:
                        filter_conditions.append(getattr(cls, key) == value)
                        logger.debug(f"Filtro aplicado: {cls.__name__}.{key} == {value} (tipo: {type(value)})")
                else:
                    logger.warning(f"Filtro ignorado: {key} no está en _filterable_fields de {cls.__name__}")

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))
                logger.debug(f"Query con filtros: {len(filter_conditions)} condiciones aplicadas en {cls.__name__}")

        # Aplicar búsqueda: texto, id exacto y fechas (año, mes, día)
        if search:
            logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Término de búsqueda: '{search}', search_type: '{search_type}'")
            search_conditions = []
            is_date_search = False
            
            # Búsqueda por fechas: año, mes, día específico
            from sqlalchemy import Date, DateTime, extract
            from datetime import datetime
            
            parsed_date = None
            parsed_datetime = None
            year_only = None
            month_only = None
            day_only = None
            
            if isinstance(search, str):
                search = search.strip()
                
                # Detectar si es solo un año (4 dígitos)
                if search.isdigit() and len(search) == 4:
                    try:
                        year_only = int(search)
                        is_date_search = True
                    except ValueError:
                        pass
                
                # Detectar formatos con barra o guión
                elif '-' in search or '/' in search:
                    try:
                        parts = search.replace('/', '-').split('-')
                        parts = [p for p in parts if p]  # Remover partes vacías (ej: "7/9/" → ["7", "9"])

                        if len(parts) == 2:
                            # Puede ser YYYY-MM, DD-MM, o MM-DD
                            first = int(parts[0])
                            second = int(parts[1])

                            # Si el primer número tiene 4 dígitos, es año-mes (YYYY-MM)
                            if len(parts[0]) == 4:
                                year_only = first
                                month_only = second
                                is_date_search = True
                                logger.debug(f"[SEARCH DEBUG] Detectado año-mes: {year_only}-{month_only}")
                            # Si ambos son <= 31, asumimos día-mes o mes-día
                            elif first <= 31 and second <= 12:
                                # Asumimos formato DD/MM (día/mes) - común en Latinoamérica
                                day_only = first
                                month_only = second
                                is_date_search = True
                                logger.debug(f"[SEARCH DEBUG] Detectado día-mes: {day_only}/{month_only}")
                            elif first <= 12 and second <= 31:
                                # Podría ser MM/DD, pero priorizamos DD/MM
                                day_only = first
                                month_only = second
                                is_date_search = True
                                logger.debug(f"[SEARCH DEBUG] Detectado día-mes (ambiguo): {day_only}/{month_only}")
                    except (ValueError, IndexError) as e:
                        logger.debug(f"[SEARCH DEBUG] Error parseando formato fecha con separador: {e}")
                        pass
                
                # Intentar parsear como fecha completa
                else:
                    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']
                    datetime_formats = [
                        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                        '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'
                    ]
                    
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(search, fmt).date()
                            is_date_search = True
                            break
                        except Exception:
                            continue
                    
                    if not parsed_date:
                        for fmt in datetime_formats:
                            try:
                                parsed_datetime = datetime.strptime(search, fmt)
                                is_date_search = True
                                break
                            except Exception:
                                continue

            # Aplicar búsqueda según el tipo especificado
            if search_type == 'dates':
                # Búsqueda SOLO en campos de fecha (cuando se especifica explícitamente)
                try:
                    for col in cls.__table__.columns:
                        if isinstance(col.type, (Date, DateTime)):
                            col_attr = getattr(cls, col.name)

                            # Búsqueda por día Y mes combinados (ej: 7/9 = día 7, mes 9)
                            if day_only is not None and month_only is not None:
                                search_conditions.append(
                                    and_(
                                        extract('day', col_attr) == day_only,
                                        extract('month', col_attr) == month_only
                                    )
                                )

                            # Búsqueda por año solo
                            elif year_only is not None and month_only is None:
                                search_conditions.append(extract('year', col_attr) == year_only)

                            # Búsqueda por año-mes
                            elif year_only is not None and month_only is not None:
                                search_conditions.append(
                                    and_(
                                        extract('year', col_attr) == year_only,
                                        extract('month', col_attr) == month_only
                                    )
                                )

                            # Búsqueda solo por mes
                            elif month_only is not None:
                                search_conditions.append(extract('month', col_attr) == month_only)

                            # Búsqueda por fecha completa
                            elif parsed_date is not None:
                                if isinstance(col.type, Date):
                                    search_conditions.append(col_attr == parsed_date)
                                elif isinstance(col.type, DateTime):
                                    search_conditions.append(db.func.date(col_attr) == parsed_date)

                            # Búsqueda por datetime completo
                            if parsed_datetime is not None and isinstance(col.type, DateTime):
                                search_conditions.append(col_attr == parsed_datetime)

                except Exception:
                    pass

            elif search_type == 'text' or search_type == 'auto':
                # Búsqueda en campos de texto y numéricos
                # Para 'auto': siempre buscar en texto/números, y ADEMÁS en fechas si parece fecha
                all_text_fields = set(cls._searchable_fields) if cls._searchable_fields else set()

                # Agregar todas las columnas de tipo texto del modelo
                from sqlalchemy import String, Text, Integer, BigInteger, Numeric
                for col in cls.__table__.columns:
                    if isinstance(col.type, (String, Text)) and col.name not in ['created_at', 'updated_at']:
                        all_text_fields.add(col.name)

                # Aplicar búsqueda ILIKE en todos los campos de texto
                for field in all_text_fields:
                    if hasattr(cls, field):
                        try:
                            search_conditions.append(getattr(cls, field).ilike(f'%{search}%'))
                        except Exception:
                            # Ignorar campos no compatibles con ilike
                            pass

                # Coincidencia exacta/parcial en campos numéricos si el término es numérico
                try:
                    # Intentar convertir a número para búsqueda exacta
                    numeric_val = int(str(search))
                    logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Búsqueda numérica detectada: {numeric_val}")

                    # Búsqueda exacta por ID
                    if hasattr(cls, 'id'):
                        search_conditions.append(getattr(cls, 'id') == numeric_val)
                        logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Agregada condición: id == {numeric_val}")

                    # Búsqueda exacta en TODOS los campos numéricos
                    for col in cls.__table__.columns:
                        if isinstance(col.type, (Integer, BigInteger, Numeric)) and col.name != 'id':
                            try:
                                search_conditions.append(getattr(cls, col.name) == numeric_val)
                                logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Agregada condición: {col.name} == {numeric_val}")
                            except Exception as e:
                                logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Error en campo {col.name}: {e}")

                    # Búsqueda parcial: convertir columnas numéricas a string para búsqueda tipo LIKE
                    # Útil para números largos como identificaciones donde se busca parte del número
                    for col in cls.__table__.columns:
                        if isinstance(col.type, (Integer, BigInteger)) and col.name != 'id':
                            try:
                                # CAST a texto para permitir búsquedas parciales en números
                                from sqlalchemy import cast, String as SQLString
                                search_conditions.append(
                                    cast(getattr(cls, col.name), SQLString).ilike(f'%{search}%')
                                )
                                logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Agregada condición CAST: CAST({col.name} AS TEXT) ILIKE '%{search}%'")
                            except Exception as e:
                                logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Error en CAST de campo {col.name}: {e}")

                except (ValueError, TypeError):
                    # Si no es numérico, solo buscar en campos de texto
                    logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Búsqueda NO numérica")
                    pass

                # Si 'auto' detectó que parece fecha, TAMBIÉN buscar en fechas
                if search_type == 'auto' and is_date_search:
                    logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Búsqueda AUTO: también buscando en fechas")
                    try:
                        for col in cls.__table__.columns:
                            if isinstance(col.type, (Date, DateTime)):
                                col_attr = getattr(cls, col.name)

                                # Búsqueda por día Y mes combinados (ej: 7/9 = día 7, mes 9)
                                if day_only is not None and month_only is not None:
                                    search_conditions.append(
                                        and_(
                                            extract('day', col_attr) == day_only,
                                            extract('month', col_attr) == month_only
                                        )
                                    )
                                    logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Agregada condición: DAY({col.name}) == {day_only} AND MONTH({col.name}) == {month_only}")

                                # Búsqueda por año
                                elif year_only is not None and month_only is None:
                                    search_conditions.append(extract('year', col_attr) == year_only)

                                # Búsqueda por año-mes
                                elif year_only is not None and month_only is not None:
                                    search_conditions.append(
                                        and_(
                                            extract('year', col_attr) == year_only,
                                            extract('month', col_attr) == month_only
                                        )
                                    )

                                # Búsqueda solo por mes
                                elif month_only is not None:
                                    search_conditions.append(extract('month', col_attr) == month_only)

                                # Búsqueda por fecha completa
                                elif parsed_date is not None:
                                    if isinstance(col.type, Date):
                                        search_conditions.append(col_attr == parsed_date)
                                    elif isinstance(col.type, DateTime):
                                        search_conditions.append(db.func.date(col_attr) == parsed_date)

                                # Búsqueda por datetime completo
                                if parsed_datetime is not None and isinstance(col.type, DateTime):
                                    search_conditions.append(col_attr == parsed_datetime)

                    except Exception:
                        pass
            
            elif search_type == 'all':
                # Búsqueda en todos los campos (texto, ID, y fechas)

                # Búsqueda por texto
                all_text_fields = set(cls._searchable_fields) if cls._searchable_fields else set()
                from sqlalchemy import String, Text, Integer, BigInteger, Numeric
                for col in cls.__table__.columns:
                    if isinstance(col.type, (String, Text)) and col.name not in ['created_at', 'updated_at']:
                        all_text_fields.add(col.name)

                for field in all_text_fields:
                    if hasattr(cls, field):
                        try:
                            search_conditions.append(getattr(cls, field).ilike(f'%{search}%'))
                        except Exception:
                            pass

                # Búsqueda en campos numéricos si el término es numérico
                try:
                    numeric_val = int(str(search))

                    # Búsqueda exacta por ID
                    if hasattr(cls, 'id'):
                        search_conditions.append(getattr(cls, 'id') == numeric_val)

                    # Búsqueda exacta en TODOS los campos numéricos
                    for col in cls.__table__.columns:
                        if isinstance(col.type, (Integer, BigInteger, Numeric)) and col.name != 'id':
                            try:
                                search_conditions.append(getattr(cls, col.name) == numeric_val)
                            except Exception:
                                pass

                    # Búsqueda parcial en campos numéricos (CAST a texto)
                    for col in cls.__table__.columns:
                        if isinstance(col.type, (Integer, BigInteger)) and col.name != 'id':
                            try:
                                from sqlalchemy import cast, String as SQLString
                                search_conditions.append(
                                    cast(getattr(cls, col.name), SQLString).ilike(f'%{search}%')
                                )
                            except Exception:
                                pass

                except (ValueError, TypeError):
                    pass
                
                # Búsqueda por fechas
                try:
                    for col in cls.__table__.columns:
                        if isinstance(col.type, (Date, DateTime)):
                            col_attr = getattr(cls, col.name)

                            # Búsqueda por día Y mes combinados (ej: 7/9 = día 7, mes 9)
                            if day_only is not None and month_only is not None:
                                search_conditions.append(
                                    and_(
                                        extract('day', col_attr) == day_only,
                                        extract('month', col_attr) == month_only
                                    )
                                )

                            # Búsqueda por año solo
                            elif year_only is not None and month_only is None:
                                search_conditions.append(extract('year', col_attr) == year_only)

                            # Búsqueda por año-mes
                            elif year_only is not None and month_only is not None:
                                search_conditions.append(
                                    and_(
                                        extract('year', col_attr) == year_only,
                                        extract('month', col_attr) == month_only
                                    )
                                )

                            # Búsqueda solo por mes
                            elif month_only is not None:
                                search_conditions.append(extract('month', col_attr) == month_only)

                            # Búsqueda por fecha completa
                            elif parsed_date is not None:
                                if isinstance(col.type, Date):
                                    search_conditions.append(col_attr == parsed_date)
                                elif isinstance(col.type, DateTime):
                                    search_conditions.append(db.func.date(col_attr) == parsed_date)

                            # Búsqueda por datetime completo
                            if parsed_datetime is not None and isinstance(col.type, DateTime):
                                search_conditions.append(col_attr == parsed_datetime)

                except Exception:
                    pass

            if search_conditions:
                logger.debug(f"[SEARCH DEBUG] {cls.__name__} - Total de condiciones de búsqueda: {len(search_conditions)}")
                query = query.filter(or_(*search_conditions))
            else:
                logger.debug(f"[SEARCH DEBUG] {cls.__name__} - NO se generaron condiciones de búsqueda")

        # Aplicar ordenamiento
        if sort_by and sort_by in cls._sortable_fields and hasattr(cls, sort_by):
            order_func = asc if sort_order.lower() == 'asc' else desc
            query = query.order_by(order_func(getattr(cls, sort_by)))
        else:
            # Orden por defecto robusto:
            # 1) updated_at desc para reflejar cambios recientes
            # 2) created_at desc para nuevos registros
            # 3) id desc como fallback estable ante valores nulos o desfases de tiempo
            try:
                query = query.order_by(
                    desc(getattr(cls, 'updated_at')),
                    desc(getattr(cls, 'created_at')),
                    desc(getattr(cls, 'id'))
                )
            except Exception:
                # Fallback mínimo si alguna columna no existe
                query = query.order_by(desc(cls.id))

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
        """Crear múltiples instancias de forma optimizada con sincronización completa."""
        instances = [cls(**cls._validate_and_normalize(data)) for data in items_data]
        db.session.add_all(instances)
        db.session.flush()  # Obtener IDs generados
        db.session.commit()  # Persistir en BD
        # Refrescar todas las instancias para sincronizar con BD
        for instance in instances:
            db.session.refresh(instance)
        return instances

    @classmethod
    def bulk_update(cls, updates_data):
        """Actualizar múltiples instancias de forma optimizada con sincronización completa."""
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

        db.session.flush()  # Aplicar cambios antes del commit
        db.session.commit()  # Persistir en BD
        # Refrescar todas las instancias para sincronizar con BD
        for instance in updated_instances:
            db.session.refresh(instance)
        return updated_instances


    def save(self):
        """Persistir cambios en DB con actualización de timestamp y sincronización completa."""
        from datetime import datetime, timezone
        try:
            self.updated_at = datetime.now(timezone.utc)
        except Exception:
            pass
        db.session.add(self)
        db.session.flush()  # Obtener IDs generados y aplicar defaults de BD
        db.session.commit()  # Persistir en BD
        db.session.refresh(self)  # Sincronizar instancia con datos reales de BD
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
                    # Verificar si la relación es dinámica antes de aplicar selectinload
                    relation_attr = getattr(cls, relation_name)
                    if hasattr(relation_attr.property, 'lazy') and relation_attr.property.lazy == 'dynamic':
                        continue  # Saltar relaciones dinámicas
                    query = query.options(selectinload(relation_attr))
        
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
                    # Verificar si la relación es dinámica antes de aplicar selectinload
                    relation_attr = getattr(cls, relation_name)
                    if hasattr(relation_attr.property, 'lazy') and relation_attr.property.lazy == 'dynamic':
                        continue  # Saltar relaciones dinámicas
                    query = query.options(selectinload(relation_attr))
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
                    # Verificar si la relación es dinámica antes de aplicar selectinload
                    relation_attr = getattr(cls, relation_name)
                    if hasattr(relation_attr.property, 'lazy') and relation_attr.property.lazy == 'dynamic':
                        continue  # Saltar relaciones dinámicas
                    query = query.options(selectinload(relation_attr))

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
