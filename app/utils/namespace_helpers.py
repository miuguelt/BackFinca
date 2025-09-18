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
from app.utils.response_handler import APIResponse
from app.models.base_model import ValidationError
import logging
import csv
import io
import time
from functools import wraps

logger = logging.getLogger(__name__)


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


_LIST_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 15  # TTL corto para evitar datos muy desactualizados


def _cache_get(model_name: str, key: str):
    bucket = _LIST_CACHE.get(model_name)
    if not bucket:
        return None
    entry = bucket.get(key)
    if not entry:
        return None
    if time.time() - entry['ts'] > _CACHE_TTL_SECONDS:
        # Expirado
        try:
            del bucket[key]
        except KeyError:
            pass
        return None
    return entry['value']


def _cache_set(model_name: str, key: str, value: Any):
    bucket = _LIST_CACHE.setdefault(model_name, {})
    bucket[key] = {'value': value, 'ts': time.time()}


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
        'search': 'Texto de búsqueda simple',
        'sort_by': 'Campo para ordenar',
        'sort_order': 'asc o desc',
        'include_relations': 'true para incluir relaciones configuradas',
        'cache_bust': '1 para ignorar caché',
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
                if cache_enabled and request.args.get('cache_bust') != '1':
                    cached_payload = _cache_get(model_key, cache_key)
                    if cached_payload:
                        # Ya es respuesta completa estandarizada
                        return flask_make_response(jsonify(cached_payload), 200)

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
                sort_by = request.args.get('sort_by', type=str)
                sort_order = request.args.get('sort_order', default='asc', type=str)
                include_rel = _parse_bool(request.args.get('include_relations'))

                filters = {}
                for field in getattr(model_class, '_filterable_fields', []):
                    if field in request.args:
                        raw = request.args.get(field)
                        if raw and ',' in raw:
                            filters[field] = [v for v in raw.split(',') if v]
                        else:
                            filters[field] = raw

                query_or_paginated = model_class.get_namespace_query(
                    filters=filters or None,
                    search=search,
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
                fields_param = request.args.get('fields')
                if fields_param:
                    selected = [f.strip() for f in fields_param.split(',') if f.strip()]
                    if selected:
                        items = [
                            {k: v for k, v in obj.items() if k in selected}
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
                if cache_enabled:
                    _cache_set(model_key, cache_key, response_payload)
                headers = {'ETag': f"W/{total_val}-{max_updated}"} if max_updated else {}
                resp = flask_make_response(jsonify(response_payload), 200)
                for k, v in headers.items():
                    resp.headers[k] = v
                return resp
                
            except Exception as e:
                logger.error(f"Error listando {model_class.__name__}: {e}", exc_info=True)
                from app.utils.response_handler import APIResponse
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

                instance = model_class.create(**payload)
                result = instance.to_namespace_dict()
                logger.info(f"{model_class.__name__} created successfully with ID: {instance.id}")
                
                return APIResponse.created(result, message=f'{model_class.__name__} creado exitosamente')
                
            except ValidationError as ve:
                logger.warning(f"Validation error creating {model_class.__name__}: {ve.message}")
                return APIResponse.validation_error({'error': ve.message})
            except Exception as e:
                logger.error(f"Error creando {model_class.__name__}: {e}", exc_info=True)
                return APIResponse.error('Error interno del servidor', details={'error': str(e), 'context': f'create {model_class.__name__}'})

    class ModelDetailResource(Resource):
        @ns.doc('get_' + name, description='Obtener detalle por ID (soporta include_relations)')
        @_maybe_rate_limit
        def get(self, record_id: int):  # Retrieve
            try:
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
                return resp
            except Exception as e:
                logger.error(f"Error obteniendo {model_class.__name__} ID {record_id}: {e}", exc_info=True)
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

                instance.update(**payload)
                return APIResponse.success(data=instance.to_namespace_dict(), message=f'{name.capitalize()} actualizado exitosamente')

            except ValidationError as ve:
                logger.warning(f"Validation error updating {model_class.__name__} id={record_id}: {ve.message}")
                return APIResponse.validation_error({'error': ve.message})
            except Exception as e:
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

                    instance.update(**payload)
                    return APIResponse.success(data=instance.to_namespace_dict(), message=f'{name.capitalize()} actualizado parcialmente')

                except ValidationError as ve:
                    logger.warning(f"Validation error patching {model_class.__name__} id={record_id}: {ve.message}")
                    return APIResponse.validation_error({'error': ve.message})
                except Exception as e:
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
                instance.delete()
                body, status = APIResponse.success(data={'deleted_id': record_id}, message=f'{name.capitalize()} eliminado exitosamente')
                return flask_make_response(jsonify(body), status)
            except Exception as e:
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
                    instances = model_class.bulk_create(payload)
                    return APIResponse.created(
                        [inst.to_namespace_dict() for inst in instances],
                        message=f'{len(instances)} registros creados'
                    )
                except ValidationError as ve:
                    return APIResponse.validation_error({'error': ve.message})
                except Exception as e:
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
