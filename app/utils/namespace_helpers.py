"""Factory optimizado para creación de namespaces CRUD con mínima repetición.

Mejoras incluidas:
 - Modelos Swagger automáticos (Input / Response / List + meta de paginación)
 - CRUD estándar: GET list (filtros, búsqueda, orden, paginación), POST, GET/<id>, PUT, PATCH, DELETE
 - Endpoint adicional: /bulk (creación masiva), /stats (estadísticas básicas si el modelo las provee)
 - Respuestas consistentes (mantiene compatibilidad con marshal de Flask-RESTX) + APIResponse para errores
 - Filtros (?campo=valor1,valor2) según _filterable_fields
 - Búsqueda (?search=texto) en _searchable_fields
 - Orden (?sort_by=campo&sort_order=asc|desc) restringido a _sortable_fields
 - Relaciones (?include_relations=true)
 - Caché ligera en memoria para listados (TTL corto) desactivable con ?cache_bust=1
 - ETag simple (basado en total + timestamp de actualización más reciente en la página)
 - Preparado para integrar rate limiting (si un decorador externo se inyecta)

Las optimizaciones buscan equilibrio entre simplicidad y funcionalidades útiles sin reintroducir complejidad excesiva.
"""

from flask_restx import Namespace, Resource, fields
from flask import request, make_response, jsonify
from typing import Dict, List, Type, Any, Optional, Callable
from app import db
from app.utils.response_handler import APIResponse
from app.models.base_model import ValidationError
import logging
import csv
import io
import time
import hashlib
from datetime import datetime
from functools import wraps
from collections import OrderedDict
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

logger = logging.getLogger(__name__)

# Versión de la API para headers
API_VERSION = "1.0.0"

# Configuración de caché LRU
MAX_CACHE_ENTRIES_PER_MODEL = 1000  # Máximo 1000 variantes por modelo
MAX_TOTAL_CACHE_SIZE_MB = 100  # Límite total de 100MB para todo el caché


def _field_definitions_for_model(model_class, exclude: List[str]) -> Dict[str, fields.Raw]:
    defs = {}
    for column in model_class.__table__.columns:
        if column.name in exclude:
            continue
        kwargs = {
            'description': column.name.replace('_', ' ').title(),
            'required': not column.nullable and column.default is None and column.name not in ('id',),
        }
        py_type = getattr(column.type, 'python_type', None)
        if py_type is int:
            defs[column.name] = fields.Integer(**kwargs)
        elif py_type is float:
            defs[column.name] = fields.Float(**kwargs)
        elif py_type is bool:
            defs[column.name] = fields.Boolean(**kwargs)
        elif py_type is str:
            defs[column.name] = fields.String(**kwargs)
        else:
            defs[column.name] = fields.Raw(**kwargs)
    return defs


def _build_models(ns: Namespace, model_class: Type):
    # Build base field definitions
    input_fields = _field_definitions_for_model(model_class, exclude=['id', 'created_at', 'updated_at'])
    response_fields = _field_definitions_for_model(model_class, exclude=['password'])

    # If password column exists include it as string in input (optional) but never in response
    if 'password' in model_class.__table__.columns:
        input_fields['password'] = fields.String(description='Password (raw, will be hashed)', required=False)
        # Ensure enums appear as simple string fields in swagger (adjust existing Raw)
    for fname, col in model_class.__table__.columns.items():
        # Check if it's an enum column (SQLAlchemy Enum type)
        is_enum = (hasattr(col.type, 'enums') or 
                  str(col.type).startswith('ENUM') or
                  hasattr(col.type, 'enum_class') or
                  (hasattr(model_class, '_enum_fields') and fname in model_class._enum_fields))
        
        if is_enum:
            # Replace in input/response if present
            if fname in input_fields:
                enum_values = None
                if hasattr(model_class, '_enum_fields') and fname in model_class._enum_fields:
                    enum_class = model_class._enum_fields[fname]
                    enum_values = [e.value for e in enum_class]
                    description = f"{input_fields[fname].description}. Valores válidos: {', '.join(enum_values)}"
                else:
                    description = input_fields[fname].description
                input_fields[fname] = fields.String(description=description, required=getattr(input_fields[fname], 'required', False))
            if fname in response_fields:
                response_fields[fname] = fields.String(description=response_fields[fname].description, required=False)

    input_model = ns.model(f'{model_class.__name__}Input', input_fields)
    response_model = ns.model(f'{model_class.__name__}Response', response_fields)
    # Modelo de paginación acorde al contrato unificado APIResponse.paginated_success
    pagination_model = ns.model('PaginationMeta', {
        'page': fields.Integer(description='Página actual'),
        'limit': fields.Integer(description='Elementos por página'),
        'total_items': fields.Integer(description='Total de elementos'),
        'total_pages': fields.Integer(description='Total de páginas'),
        'has_next_page': fields.Boolean(description='¿Existe página siguiente?'),
        'has_previous_page': fields.Boolean(description='¿Existe página anterior?'),
    })
    list_model = ns.model(f'{model_class.__name__}List', {
        'success': fields.Boolean(description='Indicador de éxito'),
        'data': fields.List(fields.Nested(response_model), description='Lista paginada de elementos'),
        'meta': fields.Nested(ns.model('ListMeta', {
            'pagination': fields.Nested(pagination_model)
        }), description='Metadatos adicionales (paginación)')
    })
    return input_model, response_model, list_model


def _parse_bool(val: Any, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ('1', 'true', 'yes', 'y')


class LRUCache:
    """Cache LRU (Least Recently Used) con límite de tamaño.

    Evita memory leaks manteniendo solo las entradas más recientes.
    Cuando se alcanza el límite, elimina las entradas más antiguas.
    """

    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key):
        """Obtener valor y mover al final (más reciente)."""
        if key in self.cache:
            self.hits += 1
            # Mover al final (más reciente)
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, key, value):
        """Guardar valor y aplicar política LRU si es necesario."""
        if key in self.cache:
            # Actualizar valor existente
            self.cache.move_to_end(key)
            self.cache[key] = value
        else:
            # Nuevo valor
            self.cache[key] = value
            # Aplicar límite de tamaño
            if len(self.cache) > self.max_size:
                # Eliminar el más antiguo (primero en OrderedDict)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"LRU eviction: removed oldest cache entry")

    def clear(self):
        """Limpiar todo el caché."""
        self.cache.clear()

    def size(self):
        """Tamaño actual del caché."""
        return len(self.cache)

    def stats(self):
        """Estadísticas del caché."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f'{hit_rate:.1f}%'
        }


# Cache global: cada modelo tiene su propio LRUCache
_LIST_CACHE: Dict[str, LRUCache] = {}
_DETAIL_CACHE: Dict[str, LRUCache] = {}


def _get_cache_key_with_user(model_name: str, base_key: str, model_class) -> str:
    """Genera una cache key incluyendo user_id si el modelo es privado."""
    cache_config = getattr(model_class, '_cache_config', {})
    cache_type = cache_config.get('type', 'private')

    if cache_type == 'public':
        return base_key

    # Para caché privada, incluir user_id en la key
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}:{base_key}"
    except (NoAuthorizationError, Exception):
        pass

    return f"anonymous:{base_key}"


def _get_cache_ttl(model_class) -> int:
    """Obtiene el TTL configurado para un modelo."""
    cache_config = getattr(model_class, '_cache_config', {})
    return cache_config.get('ttl', 120)  # 2 minutos por defecto


def _cache_get(model_name: str, key: str, model_class, *, allow_stale: bool = False, allow_stale_seconds: int = 0):
    """Obtiene valor de caché con TTL configurable por modelo y opción de usar stale (offline)."""
    if model_name not in _LIST_CACHE:
        return (None, False)

    lru_cache = _LIST_CACHE[model_name]
    full_key = _get_cache_key_with_user(model_name, key, model_class)
    entry = lru_cache.get(full_key)

    if not entry:
        return (None, False)

    ttl = _get_cache_ttl(model_class)
    age = time.time() - entry['ts']
    if age > ttl:
        if allow_stale and age <= (ttl + allow_stale_seconds):
            return (entry['value'], True)
        return (None, False)

    return (entry['value'], False)


def _cache_set(model_name: str, key: str, value: Any, model_class):
    """Guarda valor en caché con segmentación por usuario."""
    # Crear LRUCache si no existe para este modelo
    if model_name not in _LIST_CACHE:
        _LIST_CACHE[model_name] = LRUCache(max_size=MAX_CACHE_ENTRIES_PER_MODEL)

    lru_cache = _LIST_CACHE[model_name]
    full_key = _get_cache_key_with_user(model_name, key, model_class)
    lru_cache.set(full_key, {'value': value, 'ts': time.time()})


def _cache_clear(model_name: str):
    """Invalida toda la cache de un modelo específico.

    Limpia TODAS las variantes de caché incluyendo:
    - Cache por usuario (user:{id}:...)
    - Cache anónima (anonymous:...)
    - Cache pública

    Esto garantiza que TODOS los usuarios vean datos actualizados
    después de CREATE/UPDATE/DELETE.
    """
    if model_name in _LIST_CACHE:
        lru_cache = _LIST_CACHE[model_name]
        num_entries = lru_cache.size()
        lru_cache.clear()
        logger.info(f"Cache cleared for model {model_name}: {num_entries} entries invalidated")
    if model_name in _DETAIL_CACHE:
        lru_cache = _DETAIL_CACHE[model_name]
        num_entries = lru_cache.size()
        lru_cache.clear()
        logger.info(f"Detail cache cleared for model {model_name}: {num_entries} entries invalidated")


def _detail_cache_get(model_name: str, record_id: int, model_class, *, allow_stale: bool = False, allow_stale_seconds: int = 0):
    """Obtiene valor de caché para detalle con opción de usar stale."""
    if model_name not in _DETAIL_CACHE:
        return (None, False)
    lru_cache = _DETAIL_CACHE[model_name]
    full_key = _get_cache_key_with_user(model_name, str(record_id), model_class)
    entry = lru_cache.get(full_key)
    if not entry:
        return (None, False)
    ttl = _get_cache_ttl(model_class)
    age = time.time() - entry['ts']
    if age > ttl:
        if allow_stale and age <= (ttl + allow_stale_seconds):
            return (entry['value'], True)
        return (None, False)
    return (entry['value'], False)


def _detail_cache_set(model_name: str, record_id: int, value: Any, model_class):
    """Guarda detalle en cache con segmentación por usuario."""
    if model_name not in _DETAIL_CACHE:
        _DETAIL_CACHE[model_name] = LRUCache(max_size=MAX_CACHE_ENTRIES_PER_MODEL)
    lru_cache = _DETAIL_CACHE[model_name]
    full_key = _get_cache_key_with_user(model_name, str(record_id), model_class)
    lru_cache.set(full_key, {'value': value, 'ts': time.time()})


def _detail_cache_clear(model_name: str, record_id: Optional[int] = None):
    """Invalida caché de detalle de un modelo, opcionalmente solo un ID."""
    if model_name not in _DETAIL_CACHE:
        return
    lru_cache = _DETAIL_CACHE[model_name]
    if record_id is None:
        lru_cache.clear()
        logger.info(f"Detail cache cleared for model {model_name}")
        return
    full_key_prefix = f"user:"  # se limpia por user y anónimo
    keys_to_delete = []
    for k in list(lru_cache.cache.keys()):
        if k.endswith(f":{record_id}") or k.split(':')[-1] == str(record_id):
            keys_to_delete.append(k)
    for k in keys_to_delete:
        lru_cache.cache.pop(k, None)


def _generate_cache_headers(model_class, max_updated_at=None) -> Dict[str, str]:
    """Genera headers HTTP de caché optimizados para PWA."""
    cache_config = getattr(model_class, '_cache_config', {})
    headers = {}

    # X-API-Version para versionado
    headers['X-API-Version'] = API_VERSION

    # Cache-Control header
    cache_type = cache_config.get('type', 'private')
    max_age = cache_config.get('max_age', 120)
    stale_while_revalidate = cache_config.get('stale_while_revalidate', 60)
    stale_if_error = cache_config.get('stale_if_error', 0)

    cache_control_parts = [cache_type, f'max-age={max_age}']

    if stale_while_revalidate > 0:
        cache_control_parts.append(f'stale-while-revalidate={stale_while_revalidate}')
    if stale_if_error > 0:
        cache_control_parts.append(f'stale-if-error={stale_if_error}')

    headers['Cache-Control'] = ', '.join(cache_control_parts)

    # Last-Modified header basado en el registro más reciente
    if max_updated_at:
        if isinstance(max_updated_at, str):
            try:
                max_updated_at = datetime.fromisoformat(max_updated_at.replace('Z', '+00:00'))
            except:
                pass
        if isinstance(max_updated_at, datetime):
            # Formato HTTP date (RFC 7231)
            headers['Last-Modified'] = max_updated_at.strftime('%a, %d %b %Y %H:%M:%S GMT')

    # X-Cache-Strategy hint para Service Workers
    strategy = cache_config.get('strategy', 'stale-while-revalidate')
    headers['X-Cache-Strategy'] = strategy
    if stale_if_error:
        headers['X-Stale-If-Error'] = str(stale_if_error)

    # Vary header para indicar que la respuesta puede variar según el usuario
    if cache_type == 'private':
        headers['Vary'] = 'Authorization, Cookie'
    else:
        headers['Vary'] = 'Accept-Encoding'

    return headers


def _check_conditional_request(etag: str, last_modified: str = None) -> bool:
    """Verifica si se debe retornar 304 Not Modified."""
    # Verificar If-None-Match (ETag)
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and etag:
        # Puede contener múltiples ETags separados por coma
        client_etags = [tag.strip() for tag in if_none_match.split(',')]
        if etag in client_etags or f'W/{etag}' in client_etags:
            return True

    # Verificar If-Modified-Since
    if_modified_since = request.headers.get('If-Modified-Since')
    if if_modified_since and last_modified:
        try:
            client_date = datetime.strptime(if_modified_since, '%a, %d %b %Y %H:%M:%S GMT')
            server_date = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S GMT')
            if server_date <= client_date:
                return True
        except:
            pass

    return False


def create_optimized_namespace(
    name: str,
    description: str,
    model_class: Type,
    path: str = None,
    *,
    enable_bulk: bool = True,
    enable_patch: bool = True,
    enable_stats: bool = True,
    cache_enabled: bool = True,
    rate_limit_decorator: Optional[Callable] = None,
) -> Namespace:
    """Crear namespace con CRUD auto-registrado para un modelo dado.

    Parámetros avanzados:
      enable_bulk: habilita POST /bulk para creación masiva.
      enable_patch: habilita PATCH para actualización parcial.
      enable_stats: habilita GET /stats si el modelo expone get_stats().
      cache_enabled: activa caché corta para listados.
      rate_limit_decorator: decorador opcional para aplicar rate limiting a los endpoints.
    """
    ns = Namespace(name=name, description=description, path=path or f'/{name}')

    input_model, response_model, list_model = _build_models(ns, model_class)

    def _maybe_rate_limit(func):
        if rate_limit_decorator:
            return rate_limit_decorator(func)
        return func

    # Documentar parámetros comunes del listado
    ns.doc(params={
        'page': 'Página (int)',
        'limit': 'Elementos por página (int)',
        'search': 'Texto de búsqueda simple (coincide por texto, ID exacto y fechas)',
        'sort_by': 'Campo para ordenar (alias: sort)',
        'sort_order': 'asc o desc (alias: order)',
        'include_relations': 'true para incluir relaciones configuradas',
        'cache_bust': '1 para ignorar caché',
        'prefer_cache': 'true para usar respuesta en caché incluso expirada (modo offline)',
        'offline_fallback': 'alias de prefer_cache para conexiones inestables',
        'fields': 'Lista de campos separados por coma a incluir en items (ej: id,name,status)',
        'export': 'Exportar formato (csv); si se usa, ignora paginación salvo page/limit explícitos',
        **{f: f'Filtro por campo {f}' for f in getattr(model_class, '_filterable_fields', [])}
    })
    from flask import jsonify, make_response as flask_make_response
    class ModelListResource(Resource):
        @ns.doc('list_' + name, description='Listar registros con filtros y paginación (caché ligera / export / selección de campos)')
        @_maybe_rate_limit
        def get(self):  # List
            try:
                args_items = sorted((k, v) for k, v in request.args.items() if k != 'cache_bust')
                cache_key = str(args_items)
                model_key = model_class.__name__
                cache_config = getattr(model_class, '_cache_config', {})
                stale_if_error = cache_config.get('stale_if_error', 0)
                prefer_cache = _parse_bool(request.args.get('prefer_cache')) or _parse_bool(request.args.get('offline_fallback'))
                allow_cache = cache_enabled and request.args.get('cache_bust') != '1'

                cached_payload = None
                cache_is_stale = False
                if cache_enabled or stale_if_error > 0 or prefer_cache:
                    cached_payload, cache_is_stale = _cache_get(
                        model_key,
                        cache_key,
                        model_class,
                        allow_stale=(prefer_cache or stale_if_error > 0),
                        allow_stale_seconds=stale_if_error
                    )

                if allow_cache and cached_payload and (prefer_cache or not cache_is_stale):
                    cached_meta = cached_payload.get('meta', {}).get('pagination', {})
                    cached_total = cached_meta.get('total_items', 0)
                    max_updated_cached = None
                    try:
                        if cached_payload.get('data'):
                            upd_vals = [item.get('updated_at') for item in cached_payload['data'] if item.get('updated_at')]
                            if upd_vals:
                                max_updated_cached = max(upd_vals)
                    except Exception:
                        pass

                    from datetime import datetime, timezone
                    etag = f'"{cached_total}-{max_updated_cached}"' if max_updated_cached else f'"{cached_total}-none"'
                    cache_headers = _generate_cache_headers(model_class, max_updated_cached)
                    cache_headers['X-Cache-Status'] = 'STALE' if cache_is_stale else 'HIT'
                    if cache_is_stale:
                        cache_headers['Warning'] = '110 - "Contenido en caché expirado usado por prefer_cache/offline"'

                    if _check_conditional_request(etag, cache_headers.get('Last-Modified')):
                        resp = flask_make_response('', 304)
                        resp.headers['ETag'] = etag
                        for k, v in cache_headers.items():
                            resp.headers[k] = v
                        return resp

                    resp = flask_make_response(jsonify(cached_payload), 200)
                    resp.headers['ETag'] = etag
                    for k, v in cache_headers.items():
                        resp.headers[k] = v
                    return resp

                page = request.args.get('page', type=int)
                # Accept new 'limit' param or legacy 'per_page' for compatibility
                per_page = request.args.get('limit', type=int) or request.args.get('per_page', type=int)
                if page is not None and page < 1:
                    return {
                        'success': False,
                        'error': 'Invalid pagination',
                        'message': 'page debe ser >= 1'
                    }, 400
                if per_page is not None and per_page < 1:
                    return {
                        'success': False,
                        'error': 'Invalid pagination',
                        'message': 'limit debe ser >= 1'
                    }, 400

                # Defaults seguros para evitar full scans
                if page is None:
                    page = 1
                if per_page is None:
                    per_page = 50

                search = request.args.get('search', type=str)
                search_type = request.args.get('search_type', default='auto', type=str)
                # Aceptar alias desde frontend: sort -> sort_by, order -> sort_order
                sort_by = request.args.get('sort_by', type=str) or request.args.get('sort', type=str)
                sort_order = request.args.get('sort_order', type=str) or request.args.get('order', type=str)
                # Default más seguro para UX: descendente cuando no se especifica
                if not sort_order:
                    sort_order = 'desc'
                include_rel = _parse_bool(request.args.get('include_relations'))
                # Si la búsqueda es por fechas y no se especifica include_relations,
                # activarlo por defecto para asegurar serialización completa en listados.
                try:
                    if not request.args.get('include_relations') and search_type in ('dates', 'all'):
                        include_rel = True
                except Exception:
                    pass

                filters = {}
                
                # Mapeo de campos del frontend al backend para compatibilidad
                frontend_to_backend_map = {
                    'father_id': 'idFather',
                    'mother_id': 'idMother',
                    # Nota: animal_id es el campo correcto en las tablas hijas, no animals_id
                    # Este mapeo se eliminó para evitar conflictos con el cacheo
                }
                
                # Primero mapear campos del frontend
                mapped_args = {}
                for frontend_field, backend_field in frontend_to_backend_map.items():
                    if frontend_field in request.args:
                        mapped_args[backend_field] = request.args[frontend_field]
                
                # Combinar con los argumentos originales (prioridad a los mapeados)
                combined_args = dict(request.args)
                combined_args.update(mapped_args)
                
                for field in getattr(model_class, '_filterable_fields', []):
                    if field in combined_args:
                        raw = combined_args.get(field)

                        # Convertir tipo según la columna del modelo
                        try:
                            column = getattr(model_class, field, None)
                            if column is not None and hasattr(column, 'type'):
                                column_type = column.type
                                from sqlalchemy import Enum as SQLEnum, Date, DateTime
                                import datetime as dt

                                def convert_single_value(v):
                                    """Convierte un valor según el tipo de columna"""
                                    # Enums
                                    if isinstance(column_type, SQLEnum) and field in getattr(model_class, '_enum_fields', {}):
                                        enum_class = model_class._enum_fields[field]
                                        try:
                                            return enum_class(v)
                                        except (ValueError, KeyError):
                                            logger.warning(f"Valor enum inválido para {field}: {v}")
                                            return v

                                    # Dates y DateTimes
                                    elif isinstance(column_type, (Date, DateTime)):
                                        try:
                                            if isinstance(column_type, DateTime):
                                                return dt.datetime.fromisoformat(v)
                                            else:
                                                return dt.date.fromisoformat(v)
                                        except (ValueError, TypeError):
                                            logger.warning(f"Fecha inválida para {field}: {v}")
                                            return v

                                    # Tipos primitivos
                                    elif hasattr(column_type, 'python_type'):
                                        py_type = column_type.python_type
                                        if py_type is int:
                                            return int(v)
                                        elif py_type is float:
                                            return float(v)
                                        elif py_type is bool:
                                            return v.lower() in ('true', '1', 'yes')
                                        else:
                                            return v
                                    else:
                                        return v

                                # Manejar listas de valores (múltiples filtros)
                                if raw and ',' in raw:
                                    values = [v.strip() for v in raw.split(',') if v.strip()]
                                    converted_values = []
                                    for v in values:
                                        try:
                                            converted_values.append(convert_single_value(v))
                                        except (ValueError, TypeError):
                                            converted_values.append(v)
                                    filters[field] = converted_values
                                else:
                                    # Valor único
                                    filters[field] = convert_single_value(raw)

                        except (ValueError, TypeError, AttributeError) as e:
                            # Si falla la conversión, usar el valor raw como fallback
                            logger.warning(f"No se pudo convertir filtro {field}={raw}: {e}")
                            if raw and ',' in raw:
                                filters[field] = [v.strip() for v in raw.split(',') if v.strip()]
                            else:
                                filters[field] = raw

                # Log de filtros aplicados (debug)
                if filters:
                    logger.debug(f"Filtros aplicados en {model_class.__name__}: {filters}")

                # Soporte para sincronización delta: ?since=timestamp
                # Retorna solo registros modificados/creados después de la fecha especificada
                since_param = request.args.get('since', type=str)
                if since_param:
                    try:
                        # Parsear timestamp ISO 8601 (ej: 2025-09-06T12:00:00Z)
                        from datetime import datetime as _dt
                        since_date = _dt.fromisoformat(since_param.replace('Z', '+00:00'))

                        # Agregar filtro automático en updated_at >= since_date
                        if not filters:
                            filters = {}

                        # Crear condición para obtener cambios recientes
                        filters['_since'] = since_date  # Usar '_since' especial para diferenciarlo
                        logger.debug(f"Delta sync enabled: since={since_date}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Parámetro 'since' inválido: {since_param} - {e}")

                query_or_paginated = model_class.get_namespace_query(
                    filters=filters or None,
                    search=search,
                    search_type=search_type,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    page=page,
                    per_page=per_page,
                    include_relations=include_rel
                )

                data_struct = model_class.get_paginated_response(
                    query_or_paginated, include_relations=include_rel
                )

                # Prefer unified pagination keys but fallback to legacy ones for compatibility
                items = data_struct.get('items', [])
                page_val = data_struct.get('page', 1)
                per_page_val = data_struct.get('limit', data_struct.get('per_page', len(items)))
                total_val = data_struct.get('total_items', data_struct.get('total', len(items)))
                max_updated = None
                try:
                    if items:
                        upd_vals = [it.get('updated_at') for it in items if isinstance(it, dict) and it.get('updated_at')]
                        if upd_vals:
                            max_updated = max(upd_vals)
                except Exception:
                    pass
                # Filtrado de campos (?fields=)
                # En búsquedas por fechas, devolver objetos completos y evitar recortes de columnas.
                fields_param = request.args.get('fields')
                try:
                    raw_search = request.args.get('search', type=str) or ''
                    st = (request.args.get('search_type', default='auto', type=str) or 'auto').lower()
                    # Heurística para detectar término de fecha (año, año-mes, fecha completa)
                    def _looks_like_date(s: str) -> bool:
                        s = (s or '').strip()
                        if not s:
                            return False
                        if s.isdigit() and len(s) == 4:
                            return True
                        if ('-' in s or '/' in s):
                            parts = s.replace('/', '-').split('-')
                            if len(parts) in (2, 3):
                                return all(p.isdigit() for p in parts)
                        return False

                    is_date_like = _looks_like_date(raw_search)
                    # Si es búsqueda por fechas efectiva (dates/all o auto con término de fecha), ignorar 'fields'
                    if fields_param and (st in ('dates', 'all') or (st == 'auto' and is_date_like)):
                        fields_param = None
                except Exception:
                    # Ante cualquier error, mantener comportamiento previo
                    pass

                if fields_param:
                    selected = [f.strip() for f in fields_param.split(',') if f.strip()]
                    # Agregar campos de filtro a selected para asegurar que estén en la respuesta
                    filter_fields = set(filters.keys()) if filters else set()
                    selected_set = set(selected) | filter_fields
                    if selected_set:
                        items = [
                            {k: v for k, v in obj.items() if k in selected_set}
                            for obj in items
                        ]

                # Export CSV si ?export=csv
                export_fmt = request.args.get('export')
                if export_fmt and export_fmt.lower() == 'csv':
                    output = io.StringIO()
                    # Determinar encabezados (union de keys) preservando orden de primera fila
                    headers = []
                    for it in items:
                        for k in it.keys():
                            if k not in headers:
                                headers.append(k)
                    writer = csv.DictWriter(output, fieldnames=headers)
                    writer.writeheader()
                    for row in items:
                        writer.writerow(row)
                    csv_data = output.getvalue()
                    resp = flask_make_response(csv_data, 200)
                    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
                    resp.headers['Content-Disposition'] = f'attachment; filename={model_class.__name__.lower()}_export.csv'
                    if max_updated:
                        resp.headers['ETag'] = f"W/{data_struct['total']}-{max_updated}"
                    return resp

                from app.utils.response_handler import APIResponse, ResponseFormatter
                sanitized_items = ResponseFormatter.sanitize_for_frontend(items)
                response_payload, _ = APIResponse.paginated_success(
                    data=sanitized_items,
                    page=page_val,
                    limit=per_page_val,
                    total_items=total_val,
                    message=f'Lista de {name} obtenida exitosamente'
                )
                # Debug: log the response payload to help trace test failures where
                # an item appears in the list but detail GET returns 404.
                logger.debug(f"List response payload for {model_class.__name__}: {response_payload}")

                # Generar ETag estable basado en datos reales (total y último updated_at)
                from datetime import datetime, timezone
                etag = f'"{total_val}-{max_updated}"' if max_updated else f'"{total_val}-none"'
                pwa_headers = _generate_cache_headers(model_class, max_updated)

                # Verificar si el cliente ya tiene esta versión
                if _check_conditional_request(etag, pwa_headers.get('Last-Modified')):
                    # Cliente tiene versión válida, retornar 304 Not Modified
                    resp = flask_make_response('', 304)
                    resp.headers['ETag'] = etag
                    for k, v in pwa_headers.items():
                        resp.headers[k] = v
                    return resp

                # Guardar en caché DESPUÉS de verificar 304
                if cache_enabled:
                    _cache_set(model_key, cache_key, response_payload, model_class)

                # Retornar respuesta completa con headers PWA
                resp = flask_make_response(jsonify(response_payload), 200)
                resp.headers['ETag'] = etag
                for k, v in pwa_headers.items():
                    resp.headers[k] = v

                # Header X-Has-More para paginación infinita en PWA
                pagination_meta = response_payload.get('meta', {}).get('pagination', {})
                if pagination_meta.get('has_next_page', False):
                    resp.headers['X-Has-More'] = 'true'
                else:
                    resp.headers['X-Has-More'] = 'false'

                # Header X-Total-Count para ayudar a PWA a dimensionar carga
                resp.headers['X-Total-Count'] = str(total_val)

                return resp
                
            except Exception as e:
                logger.error(f"Error listando {model_class.__name__}: {e}", exc_info=True)
                from app.utils.response_handler import APIResponse

                # Intentar fallback a caché stale si existe y está permitido
                if cached_payload and stale_if_error > 0:
                    try:
                        cached_meta = cached_payload.get('meta', {}).get('pagination', {})
                        cached_total = cached_meta.get('total_items', 0)
                        max_updated_cached = None
                        try:
                            if cached_payload.get('data'):
                                upd_vals = [item.get('updated_at') for item in cached_payload['data'] if item.get('updated_at')]
                                if upd_vals:
                                    max_updated_cached = max(upd_vals)
                        except Exception:
                            pass

                        etag = f'"{cached_total}-{max_updated_cached}"' if max_updated_cached else f'"{cached_total}-none"'
                        cache_headers = _generate_cache_headers(model_class, max_updated_cached)
                        cache_headers['X-Cache-Status'] = 'STALE-FALLBACK'
                        cache_headers['Warning'] = '111 - "Respuesta en caché servida por error de backend"'
                        cache_headers['X-Offline-Fallback'] = 'true'
                        resp = flask_make_response(jsonify(cached_payload), 200)
                        resp.headers['ETag'] = etag
                        for k, v in cache_headers.items():
                            resp.headers[k] = v
                        return resp
                    except Exception:
                        logger.debug("No se pudo usar fallback de caché tras error de backend", exc_info=True)

                resp_body, status = APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'list {model_class.__name__}'})
                resp = flask_make_response(jsonify(resp_body), status)
                return resp

        @_maybe_rate_limit
        @ns.doc('head_list_' + name, description='HEAD listado: devuelve solo headers (ETag, status) sin cuerpo')
        def head(self):  # HEAD same metadata without body
            resp = self.get()
            # resp may be (body, status) or (body, status, headers)
            if isinstance(resp, tuple):
                if len(resp) == 3:
                    return '', resp[1], resp[2]
                elif len(resp) == 2:
                    return '', resp[1]
            return '', 200

        @ns.doc('create_' + name, description='Crear nuevo registro')
        @ns.expect(input_model, validate=False)  # Validación manual para mejor control
        @_maybe_rate_limit
        def post(self):  # Create
            try:
                payload = request.get_json(force=True, silent=True)
                if not payload or not isinstance(payload, dict):
                    return APIResponse.validation_error({'payload': 'Se requiere un objeto JSON válido y no vacío.'})

                logger.info(f"Creating {model_class.__name__} with payload: {payload}")
                # Convert ISO date/datetime strings into Python objects for DB drivers
                try:
                    from sqlalchemy import Date, DateTime
                    import datetime as _dt
                    for col in model_class.__table__.columns:
                        cname = col.name
                        if cname in payload and isinstance(payload[cname], str):
                            try:
                                if isinstance(col.type, Date):
                                    payload[cname] = _dt.date.fromisoformat(payload[cname])
                                elif isinstance(col.type, DateTime):
                                    # datetime.fromisoformat handles both naive and offset-aware
                                    payload[cname] = _dt.datetime.fromisoformat(payload[cname])
                            except Exception:
                                # Leave as-is; let model validation handle the error
                                pass
                except Exception:
                    # If sqlalchemy types not available or conversion fails, continue
                    pass

                # Remap input aliases if model provides them (legacy keys)
                try:
                    aliases = getattr(model_class, '_input_aliases', {}) or {}
                    for k, v in list(payload.items()):
                        if k in aliases and aliases[k] not in payload:
                            payload[aliases[k]] = payload.pop(k)
                except Exception:
                    pass

                # Crear registro (commit incluido en model_class.create())
                logger.debug(f"Creating {model_class.__name__} instance...")
                instance = model_class.create(**payload)
                logger.debug(f"Instance created with ID: {instance.id}")

                # Serializar INMEDIATAMENTE después de create (antes de cualquier operación que pueda detach)
                try:
                    logger.debug(f"Serializing {model_class.__name__} instance...")
                    result = instance.to_namespace_dict()
                    instance_id = instance.id
                    logger.info(f"{model_class.__name__} created successfully with ID: {instance_id}")
                except Exception as e:
                    logger.error(f"Error serializing {model_class.__name__} after create: {e}", exc_info=True)
                    # Fallback: re-query desde BD
                    logger.debug(f"Re-querying {model_class.__name__} ID {instance.id} from DB...")
                    instance = model_class.query.get(instance.id)
                    if instance:
                        result = instance.to_namespace_dict()
                        instance_id = instance.id
                        logger.info(f"{model_class.__name__} re-queried and serialized successfully with ID: {instance_id}")
                    else:
                        raise Exception(f"Failed to serialize and re-query {model_class.__name__}")

                # Invalidar cache DESPUÉS de serialización exitosa
                _cache_clear(model_class.__name__)
                _detail_cache_clear(model_class.__name__, record_id)
                logger.debug(f"Cache cleared for {model_class.__name__}")

                # Construir respuesta con datos serializados
                from flask import make_response
                response = APIResponse.created(result, message=f'{model_class.__name__} creado exitosamente')
                if isinstance(response, tuple) and len(response) >= 2:
                    resp_body, status_code = response[0], response[1]
                    resp = make_response(jsonify(resp_body), status_code)
                    # Headers para invalidar caché del cliente
                    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    resp.headers['Pragma'] = 'no-cache'
                    resp.headers['Expires'] = '0'
                    resp.headers['ETag'] = f'"{instance_id}"'
                    logger.debug(f"Response prepared for {model_class.__name__} ID {instance_id}")
                    return resp
                logger.debug(f"Returning simple response for {model_class.__name__}")
                return response

            except ValidationError as ve:
                db.session.rollback()
                logger.warning(f"Validation error creating {model_class.__name__}: {ve.message}")
                return APIResponse.validation_error({'error': ve.message})
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creando {model_class.__name__}: {e}", exc_info=True)
                return APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'create {model_class.__name__}'})

    class ModelDetailResource(Resource):
        @ns.doc('get_' + name, description='Obtener detalle por ID (soporta include_relations)')
        @_maybe_rate_limit
        def get(self, record_id: int):  # Retrieve
            try:
                cache_config = getattr(model_class, '_cache_config', {})
                stale_if_error = cache_config.get('stale_if_error', 0)
                prefer_cache = _parse_bool(request.args.get('prefer_cache')) or _parse_bool(request.args.get('offline_fallback'))
                allow_cache = cache_enabled and request.args.get('cache_bust') != '1'

                cached_payload = None
                cache_is_stale = False
                if cache_enabled or stale_if_error > 0 or prefer_cache:
                    cached_payload, cache_is_stale = _detail_cache_get(
                        model_class.__name__,
                        record_id,
                        model_class,
                        allow_stale=(prefer_cache or stale_if_error > 0),
                        allow_stale_seconds=stale_if_error
                    )

                if allow_cache and cached_payload and (prefer_cache or not cache_is_stale):
                    max_updated_cached = None
                    try:
                        data_obj = cached_payload.get('data', {})
                        max_updated_cached = data_obj.get('updated_at')
                    except Exception:
                        pass
                    etag = f'"{record_id}-{max_updated_cached}"' if max_updated_cached else f'"{record_id}-none"'
                    cache_headers = _generate_cache_headers(model_class, max_updated_cached)
                    cache_headers['X-Cache-Status'] = 'STALE' if cache_is_stale else 'HIT'
                    if cache_is_stale:
                        cache_headers['Warning'] = '110 - "Detalle en caché expirado usado por prefer_cache/offline"'
                    if _check_conditional_request(etag, cache_headers.get('Last-Modified')):
                        resp = flask_make_response('', 304)
                        resp.headers['ETag'] = etag
                        for k, v in cache_headers.items():
                            resp.headers[k] = v
                        return resp
                    resp = flask_make_response(jsonify(cached_payload), 200)
                    resp.headers['ETag'] = etag
                    for k, v in cache_headers.items():
                        resp.headers[k] = v
                    return resp

                include_relations = request.args.get('include_relations', 'false').lower() == 'true'
                instance = model_class.get_by_id(record_id, include_relations=include_relations)
                if not instance:
                    body, status = APIResponse.not_found(name.capitalize())
                    return flask_make_response(jsonify(body), status)

                fields_param = request.args.get('fields')
                data_obj = instance.to_namespace_dict(include_relations=include_relations)
                if fields_param:
                    selected = [f.strip() for f in fields_param.split(',') if f.strip()]
                    data_obj = {k: v for k, v in data_obj.items() if k in selected}
                body, status = APIResponse.success(data=data_obj, message=f'{name.capitalize()} obtenido exitosamente')
                resp = flask_make_response(jsonify(body), status)

                try:
                    etag = f'"{record_id}-{data_obj.get("updated_at")}"' if isinstance(data_obj, dict) else f'"{record_id}"'
                    pwa_headers = _generate_cache_headers(model_class, data_obj.get('updated_at') if isinstance(data_obj, dict) else None)
                    pwa_headers['X-Cache-Status'] = 'MISS'
                    resp.headers['ETag'] = etag
                    for k, v in pwa_headers.items():
                        resp.headers[k] = v
                    if cache_enabled:
                        _detail_cache_set(model_class.__name__, record_id, body, model_class)
                except Exception:
                    logger.debug("No se pudo cachear/etiquetar respuesta de detalle", exc_info=True)

                return resp
            except Exception as e:
                logger.error(f"Error obteniendo {model_class.__name__} ID {record_id}: {e}", exc_info=True)
                if cached_payload and stale_if_error > 0:
                    try:
                        max_updated_cached = None
                        try:
                            data_obj = cached_payload.get('data', {})
                            max_updated_cached = data_obj.get('updated_at')
                        except Exception:
                            pass
                        etag = f'"{record_id}-{max_updated_cached}"' if max_updated_cached else f'"{record_id}-none"'
                        cache_headers = _generate_cache_headers(model_class, max_updated_cached)
                        cache_headers['X-Cache-Status'] = 'STALE-FALLBACK'
                        cache_headers['Warning'] = '111 - "Detalle en caché servido por error de backend"'
                        cache_headers['X-Offline-Fallback'] = 'true'
                        resp = flask_make_response(jsonify(cached_payload), 200)
                        resp.headers['ETag'] = etag
                        for k, v in cache_headers.items():
                            resp.headers[k] = v
                        return resp
                    except Exception:
                        logger.debug("No se pudo usar fallback de caché para detalle tras error", exc_info=True)
                body, status = APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'get {model_class.__name__}'}, status_code=500)
                resp = flask_make_response(jsonify(body), status)
                return resp

        @ns.doc('update_' + name, description='Actualizar registro (reemplazo completo)')
        @ns.expect(input_model, validate=False)
        @_maybe_rate_limit
        def put(self, record_id: int):  # Update
            try:
                instance = model_class.get_by_id(record_id)
                if not instance:
                    return APIResponse.not_found(name.capitalize(), as_tuple=True)

                payload = request.get_json(force=True, silent=True)
                if not payload or not isinstance(payload, dict):
                    return APIResponse.validation_error({'payload': 'Se requiere un objeto JSON válido y no vacío.'})

                # Actualizar (commit incluido en instance.update())
                logger.debug(f"Updating {model_class.__name__} ID {record_id}...")
                instance.update(**payload)

                # Serializar INMEDIATAMENTE después de update
                try:
                    logger.debug(f"Serializing updated {model_class.__name__} ID {record_id}...")
                    result = instance.to_namespace_dict()
                    logger.info(f"{model_class.__name__} ID {record_id} updated successfully")
                except Exception as e:
                    logger.error(f"Error serializing {model_class.__name__} after update: {e}", exc_info=True)
                    # Fallback: re-query desde BD
                    instance = model_class.query.get(record_id)
                    if instance:
                        result = instance.to_namespace_dict()
                        logger.info(f"{model_class.__name__} ID {record_id} re-queried and serialized")
                    else:
                        raise Exception(f"Failed to serialize and re-query {model_class.__name__} ID {record_id}")

                # Invalidar cache DESPUÉS de serialización exitosa
                _cache_clear(model_class.__name__)

                # Construir respuesta
                from flask import make_response
                response = APIResponse.success(data=result, message=f'{name.capitalize()} actualizado exitosamente')
                if isinstance(response, tuple) and len(response) >= 2:
                    resp_body, status_code = response[0], response[1]
                    resp = make_response(jsonify(resp_body), status_code)
                    # Headers para invalidar caché del cliente
                    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    resp.headers['Pragma'] = 'no-cache'
                    resp.headers['Expires'] = '0'
                    resp.headers['ETag'] = f'"{instance.id}-{instance.updated_at}"' if hasattr(instance, 'updated_at') else f'"{instance.id}"'
                    return resp
                return response

            except ValidationError as ve:
                db.session.rollback()
                logger.warning(f"Validation error updating {model_class.__name__} id={record_id}: {ve.message}")
                return APIResponse.validation_error({'error': ve.message})
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error actualizando {model_class.__name__} id={record_id}: {e}", exc_info=True)
                return APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'update {model_class.__name__}'})

        if enable_patch:
            @ns.doc('patch_' + name, description='Actualizar parcialmente registro')
            @ns.expect(input_model, validate=False)
            @_maybe_rate_limit
            def patch(self, record_id: int):  # Partial update
                try:
                    instance = model_class.get_by_id(record_id)
                    if not instance:
                        return APIResponse.not_found(name.capitalize(), as_tuple=True)

                    payload = request.get_json(force=True, silent=True) or {}
                    if not isinstance(payload, dict):
                        return APIResponse.validation_error({'payload': 'Se requiere un objeto JSON.'})

                    # Actualizar parcialmente (commit incluido en instance.update())
                    logger.debug(f"Patching {model_class.__name__} ID {record_id}...")
                    instance.update(**payload)

                    # Serializar INMEDIATAMENTE después de patch
                    try:
                        logger.debug(f"Serializing patched {model_class.__name__} ID {record_id}...")
                        result = instance.to_namespace_dict()
                        logger.info(f"{model_class.__name__} ID {record_id} patched successfully")
                    except Exception as e:
                        logger.error(f"Error serializing {model_class.__name__} after patch: {e}", exc_info=True)
                        # Fallback: re-query desde BD
                        instance = model_class.query.get(record_id)
                        if instance:
                            result = instance.to_namespace_dict()
                            logger.info(f"{model_class.__name__} ID {record_id} re-queried and serialized")
                        else:
                            raise Exception(f"Failed to serialize and re-query {model_class.__name__} ID {record_id}")

                    # Invalidar cache DESPUÉS de serialización exitosa
                    _cache_clear(model_class.__name__)
                    _detail_cache_clear(model_class.__name__, record_id)

                    # Construir respuesta
                    from flask import make_response
                    response = APIResponse.success(data=result, message=f'{name.capitalize()} actualizado parcialmente')
                    if isinstance(response, tuple) and len(response) >= 2:
                        resp_body, status_code = response[0], response[1]
                        resp = make_response(jsonify(resp_body), status_code)
                        # Headers para invalidar caché del cliente
                        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                        resp.headers['Pragma'] = 'no-cache'
                        resp.headers['Expires'] = '0'
                        resp.headers['ETag'] = f'"{instance.id}-{instance.updated_at}"' if hasattr(instance, 'updated_at') else f'"{instance.id}"'
                        return resp
                    return response

                except ValidationError as ve:
                    db.session.rollback()
                    logger.warning(f"Validation error patching {model_class.__name__} id={record_id}: {ve.message}")
                    return APIResponse.validation_error({'error': ve.message})
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error patch {model_class.__name__} id={record_id}: {e}", exc_info=True)
                    return APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'patch {model_class.__name__}'})

        @ns.doc('delete_' + name, description='Eliminar registro')
        @_maybe_rate_limit
        def delete(self, record_id: int):  # Delete
            try:
                instance = model_class.get_by_id(record_id)
                if not instance:
                    body, status = APIResponse.not_found(name.capitalize())
                    return flask_make_response(jsonify(body), status)

                # Verificación de integridad referencial optimizada
                from app.utils.integrity_checker import OptimizedIntegrityChecker
                
                can_delete, warnings = OptimizedIntegrityChecker.can_delete_safely(model_class, record_id)
                
                if not can_delete:
                    # No se puede eliminar - hay dependencias que lo bloquean
                    warning_messages = [w.warning_message for w in warnings if not w.cascade_delete]
                    body, status = APIResponse.error(
                        'No se puede eliminar el registro por dependencias existentes',
                        details={
                            'warnings': [w.to_dict() for w in warnings],
                            'blocking_dependencies': len(warning_messages),
                            'messages': warning_messages
                        },
                        status_code=409  # Conflict
                    )
                    return flask_make_response(jsonify(body), status)

                # Si hay dependencias con cascade, informar antes de eliminar
                cascade_warnings = [w for w in warnings if w.cascade_delete and w.dependent_count > 0]
                if cascade_warnings:
                    logger.info(f"Eliminando {model_class.__name__} id={record_id} con {len(cascade_warnings)} dependencias en cascade")

                # Eliminar de BD (commit incluido en instance.delete())
                instance.delete()

                # Invalidar cache INMEDIATAMENTE después de commit exitoso
                _cache_clear(model_class.__name__)

                # Respuesta con información de eliminación cascade si aplica
                response_data = {'deleted_id': record_id}
                if cascade_warnings:
                    response_data['cascade_deletions'] = {
                        'total_records': sum(w.dependent_count for w in cascade_warnings),
                        'details': [w.to_dict() for w in cascade_warnings]
                    }

                body, status = APIResponse.success(
                    data=response_data,
                    message=f'{name.capitalize()} eliminado exitosamente' +
                           (f" con {sum(w.dependent_count for w in cascade_warnings)} registro(s) relacionados" if cascade_warnings else "")
                )
                resp = flask_make_response(jsonify(body), status)
                # Headers para invalidar caché del cliente
                resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                resp.headers['Pragma'] = 'no-cache'
                resp.headers['Expires'] = '0'
                # Usar timestamp actual para ETag de eliminación
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                resp.headers['ETag'] = f'"deleted-{record_id}-{now}"'
                return resp
            except Exception as e:
                # Rollback explícito en caso de error
                db.session.rollback()
                logger.error(f"Error eliminando {model_class.__name__} id={record_id}: {e}", exc_info=True)
                body, status = APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'delete {model_class.__name__}'}, status_code=500)
                return flask_make_response(jsonify(body), status)

        @_maybe_rate_limit
        @ns.doc('head_' + name, description='HEAD detalle: solo headers y estado')
        def head(self, record_id: int):  # HEAD detail
            resp = self.get(record_id)
            if isinstance(resp, tuple):
                if len(resp) >= 2:
                    if len(resp) == 3:
                        return '', resp[1], resp[2]
                    return '', resp[1]
            return '', 200

    ns.add_resource(ModelListResource, '/')
    ns.add_resource(ModelDetailResource, '/<int:record_id>')

    # ---- Metadata endpoint para PWA (revalidación ligera) ----
    @ns.route('/metadata')
    class ModelMetadataResource(Resource):
        @ns.doc('metadata_' + name, description='Obtener metadatos del recurso (total, last_modified) sin body completo - optimizado para PWA')
        @_maybe_rate_limit
        def get(self):
            """Endpoint ligero para verificar si hay cambios sin descargar datos."""
            try:
                # Optimización: 1 sola query con COUNT(*) y MAX(updated_at)
                from sqlalchemy import func
                result = db.session.query(
                    func.count(model_class.id).label('total'),
                    func.max(model_class.updated_at).label('last_modified')
                ).first()

                total_count = result.total if result else 0
                max_updated = None
                if result and result.last_modified:
                    max_updated = result.last_modified.isoformat() if hasattr(result.last_modified, 'isoformat') else str(result.last_modified)

                # Generar ETag estable basado en total y último updated_at
                from datetime import datetime, timezone
                etag = f'"{total_count}-{max_updated}"' if max_updated else f'"{total_count}-none"'
                pwa_headers = _generate_cache_headers(model_class, max_updated)
                # Forzar revalidación del cliente para metadata
                pwa_headers['Cache-Control'] = 'private, max-age=0, must-revalidate'

                # Verificar si el cliente ya tiene esta versión
                if _check_conditional_request(etag, pwa_headers.get('Last-Modified')):
                    # Cliente tiene versión válida, retornar 304 Not Modified
                    resp = flask_make_response('', 304)
                    resp.headers['ETag'] = etag
                    for k, v in pwa_headers.items():
                        resp.headers[k] = v
                    return resp

                # Retornar metadatos ligeros
                metadata = {
                    'success': True,
                    'data': {
                        'resource': name,
                        'total_count': total_count,
                        'last_modified': max_updated,
                        'etag': etag
                    }
                }

                resp = flask_make_response(jsonify(metadata), 200)
                resp.headers['ETag'] = etag
                for k, v in pwa_headers.items():
                    resp.headers[k] = v
                return resp

            except Exception as e:
                logger.error(f"Error obteniendo metadata de {model_class.__name__}: {e}", exc_info=True)
                body, status = APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)
                return flask_make_response(jsonify(body), status)

    # ---- Bulk ----
    if enable_bulk:
        @ns.route('/bulk')
        class ModelBulkResource(Resource):
            @ns.doc('bulk_create_' + name, description='Crear múltiples registros en un solo request')
            @_maybe_rate_limit
            def post(self):
                try:
                    payload = request.get_json() or []
                    if not isinstance(payload, list) or not payload:
                        return APIResponse.validation_error({'items': 'Se requiere lista de objetos no vacía'})
                    enum_fields = getattr(model_class, '_enum_fields', {})
                    if enum_fields:
                        for obj in payload:
                            for ef, enum_cls in enum_fields.items():
                                if ef in obj:
                                    try:
                                        enum_cls(obj[ef])
                                    except Exception:
                                        return APIResponse.validation_error({ef: f'Valor inválido para enum {ef}'})
                    # Crear múltiples registros (commit incluido en bulk_create())
                    logger.debug(f"Bulk creating {len(payload)} {model_class.__name__} instances...")
                    instances = model_class.bulk_create(payload)
                    logger.debug(f"{len(instances)} {model_class.__name__} instances created")

                    # Serializar INMEDIATAMENTE después de bulk_create
                    try:
                        logger.debug(f"Serializing {len(instances)} {model_class.__name__} instances...")
                        results = [inst.to_namespace_dict() for inst in instances]
                        logger.info(f"{len(results)} {model_class.__name__} instances created and serialized successfully")
                    except Exception as e:
                        logger.error(f"Error serializing {model_class.__name__} after bulk_create: {e}", exc_info=True)
                        # Fallback: re-query desde BD
                        logger.debug(f"Re-querying {len(instances)} {model_class.__name__} instances...")
                        instance_ids = [inst.id for inst in instances]
                        instances = model_class.query.filter(model_class.id.in_(instance_ids)).all()
                        results = [inst.to_namespace_dict() for inst in instances]
                        logger.info(f"{len(results)} {model_class.__name__} instances re-queried and serialized")

                    # Invalidar cache DESPUÉS de serialización exitosa
                    _cache_clear(model_class.__name__)
                    _detail_cache_clear(model_class.__name__)

                    # Construir respuesta
                    from flask import make_response
                    response = APIResponse.created(
                        results,
                        message=f'{len(results)} registros creados'
                    )
                    if isinstance(response, tuple) and len(response) >= 2:
                        resp_body, status_code = response[0], response[1]
                        resp = make_response(jsonify(resp_body), status_code)
                        # Headers para invalidar caché del cliente
                        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                        resp.headers['Pragma'] = 'no-cache'
                        resp.headers['Expires'] = '0'
                        # Usar timestamp actual para ETag de creación masiva
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc).isoformat()
                        resp.headers['ETag'] = f'"bulk-{len(instances)}-{now}"'
                        return resp
                    return response
                except ValidationError as ve:
                    db.session.rollback()
                    return APIResponse.validation_error({'error': ve.message})
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error bulk create {model_class.__name__}: {e}", exc_info=True)
                    return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)

    # ---- Stats ----
    if enable_stats and hasattr(model_class, 'get_stats'):
        @ns.route('/stats')
        class ModelStatsResource(Resource):
            @ns.doc('stats_' + name, description='Obtener estadísticas básicas del modelo')
            @_maybe_rate_limit
            def get(self):
                try:
                    stats = model_class.get_stats()
                    # Añadimos un meta vacío para mantener estructura predecible (facilita front genérico)
                    body, status = APIResponse.success(stats, message='Estadísticas obtenidas')
                    resp = flask_make_response(jsonify(body), status)
                    return resp
                except Exception as e:
                    logger.error(f"Error obteniendo stats {model_class.__name__}: {e}", exc_info=True)
                    body, status = APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)
                    return flask_make_response(jsonify(body), status)

    return ns
