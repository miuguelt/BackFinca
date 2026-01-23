import logging
import threading
import time
from typing import Optional, Dict, Any


def seed_admin_user(app, logger: Optional[logging.Logger] = None) -> None:
    """
    Crea un usuario administrador semilla si la tabla y el usuario no existen.
    Pensado para ejecutarse durante el arranque de la app (create_app).

    - identification: 99999999
    - fullname: "Admin Seed"
    - email: "admin.seed@example.com"
    - phone: "3000000000"
    - password: "password123" (hashed)
    - role: Role.Administrador
    """
    _logger = logger or logging.getLogger(__name__)

    try:
        # Importaciones diferidas para evitar ciclos de importación durante el arranque
        from app import db  # type: ignore
        from app.models.user import User, Role  # type: ignore
        from sqlalchemy import inspect as sqlalchemy_inspect, or_  # type: ignore
        from werkzeug.security import generate_password_hash  # type: ignore

        with app.app_context():
            try:
                inspector = sqlalchemy_inspect(db.engine)
                if 'user' not in inspector.get_table_names():
                    _logger.info('Skipping seed admin: tabla user no existe aún')
                    return

                # Evitar errores por restricciones UNIQUE
                existing = User.query.filter(
                    or_(
                        User.identification == 99999999,
                        User.email == 'admin.seed@example.com',
                        User.phone == '3000000000',
                    )
                ).first()

                if existing:
                    _logger.info(
                        'Usuario administrador semilla existente (id=%s ident=%s)',
                        getattr(existing, 'id', None),
                        getattr(existing, 'identification', None),
                    )
                    return

                seed_admin = User(
                    identification=99999999,
                    fullname='Admin Seed',
                    password=generate_password_hash('password123'),
                    email='admin.seed@example.com',
                    phone='3000000000',
                    address='Main HQ',
                    role=Role.Administrador,
                    status=True,
                )
                db.session.add(seed_admin)
                db.session.commit()
                _logger.info('Usuario administrador semilla creado (identification=99999999)')
            except Exception as e:
                db.session.rollback()
                _logger.warning('Error verificando/creando usuario semilla: %s', e, exc_info=True)
    except Exception as e:
        _logger.warning('No se pudo crear usuario administrador semilla: %s', e, exc_info=True)


def warmup_initial_caches(app, logger: Optional[logging.Logger] = None) -> None:
    """
    Precalienta (warmup) cachés cortas de listados usados en la primera carga
    del Dashboard para reducir la latencia del primer request.

    - No cambia funcionalidad: solo ejecuta consultas estándar y guarda
      su respuesta paginada en el caché por TTL corto del modelo.
    - Respetuoso con recursos: limita warmups a primeras páginas y evita
      relaciones pesadas.
    """
    _logger = logger or logging.getLogger(__name__)

    # Configuración con valores por defecto seguros para evitar bloqueos
    async_enabled = bool(app.config.get('CACHE_WARMUP_ASYNC', True))
    include_relations_enabled = bool(app.config.get('CACHE_WARMUP_INCLUDE_RELATIONS', False))
    per_page_default = int(app.config.get('CACHE_WARMUP_LIMIT', 5))  # reducir lote para warmup
    max_seconds = float(app.config.get('CACHE_WARMUP_MAX_SECONDS', 8.0))

    def _do_warmup():
        start = time.monotonic()
        try:
            # Import diferido para evitar ciclos durante arranque
            from app.models.animals import Animals  # type: ignore
            from app.utils.namespace_helpers import _cache_set  # type: ignore

            def _warm_model_list(model_cls, args: Dict[str, Any]) -> None:
                try:
                    # Construir consulta igual que en namespaces, sin request context
                    filters = {}
                    search = args.get('search')
                    search_type = args.get('search_type', 'auto')
                    sort_by = args.get('sort_by')
                    sort_order = args.get('sort_order', 'desc')
                    page = int(args.get('page', 1))
                    per_page = int(args.get('limit', args.get('per_page', per_page_default)))
                    include_rel = bool(str(args.get('include_relations', 'false')).lower() == 'true')

                    query = model_cls.get_namespace_query(
                        filters=filters,
                        search=search,
                        search_type=search_type,
                        sort_by=sort_by,
                        sort_order=sort_order,
                        page=page,
                        per_page=per_page,
                        include_relations=include_rel,
                    )

                    # Estructura paginada canónica
                    # Para evitar cargas pesadas en warmup, serializar sin relaciones
                    data_struct = model_cls.get_paginated_response(
                        query, include_relations=False
                    )

                    payload = {
                        'success': True,
                        'data': data_struct.get('items', []),
                        'meta': {
                            'pagination': {
                                'page': data_struct.get('page', page),
                                'limit': data_struct.get('limit', per_page),
                                'total_items': data_struct.get('total_items', data_struct.get('total', 0)),
                                'total_pages': data_struct.get('total_pages', data_struct.get('pages', 1)),
                                'has_next_page': data_struct.get('has_next_page', data_struct.get('has_next', False)),
                                'has_previous_page': data_struct.get('has_previous_page', data_struct.get('has_prev', False)),
                            }
                        }
                    }

                    # Clave de caché igual que ModelListResource (args ordenados)
                    cache_key = str(sorted([(k, str(v)) for k, v in {
                        'page': page,
                        'limit': per_page,
                        'search': search or '',
                        'search_type': search_type,
                        'sort_by': sort_by or '',
                        'sort_order': sort_order,
                        'include_relations': 'false',  # warmup sin relaciones para rendimiento
                    }.items()]))

                    _cache_set(model_cls.__name__, cache_key, payload, model_cls)
                    _logger.info('Cache warmup listo para %s key=%s', model_cls.__name__, cache_key)
                except Exception as e:
                    _logger.warning('Fallo warmup para %s: %s', getattr(model_cls, '__name__', model_cls), e, exc_info=True)

            with app.app_context():
                # Warmup mínimo de animales: primera página sin relaciones y orden reciente
                _warm_model_list(Animals, {
                    'page': 1,
                    'limit': per_page_default,
                    'search_type': 'all',
                    'sort_by': 'updated_at',
                    'sort_order': 'desc',
                    'include_relations': 'false',
                })

                # Warmup con relaciones sólo si se habilita explícitamente y queda tiempo presupuesto
                if include_relations_enabled and (time.monotonic() - start) < max_seconds:
                    try:
                        # Enriquecer con relaciones ligeras sólo para mejorar UX inicial sin bloquear
                        query = Animals.get_namespace_query(
                            filters={},
                            search=None,
                            search_type='all',
                            sort_by='updated_at',
                            sort_order='desc',
                            page=1,
                            per_page=per_page_default,
                            include_relations=True,
                        )

                        # Serializar SÓLO campos base para evitar relaciones dinámicas pesadas
                        data_struct = Animals.get_paginated_response(query, include_relations=False)
                        payload = {
                            'success': True,
                            'data': data_struct.get('items', []),
                            'meta': {
                                'pagination': {
                                    'page': data_struct.get('page', 1),
                                    'limit': data_struct.get('limit', per_page_default),
                                    'total_items': data_struct.get('total_items', data_struct.get('total', 0)),
                                    'total_pages': data_struct.get('total_pages', data_struct.get('pages', 1)),
                                    'has_next_page': data_struct.get('has_next_page', data_struct.get('has_next', False)),
                                    'has_previous_page': data_struct.get('has_previous_page', data_struct.get('has_prev', False)),
                                }
                            }
                        }
                        cache_key = str(sorted([(k, str(v)) for k, v in {
                            'page': 1,
                            'limit': per_page_default,
                            'search': '',
                            'search_type': 'all',
                            'sort_by': 'updated_at',
                            'sort_order': 'desc',
                            'include_relations': 'true',
                        }.items()]))
                        _cache_set(Animals.__name__, cache_key, payload, Animals)
                        _logger.info('Cache warmup mínimo con relaciones listo para %s key=%s', Animals.__name__, cache_key)
                    except Exception as e:
                        _logger.warning('Fallo warmup con relaciones: %s', e, exc_info=True)
        except Exception as e:
            _logger.warning('Warmup inicial de caché falló: %s', e, exc_info=True)

    try:
        if async_enabled:
            th = threading.Thread(target=_do_warmup, name='cache-warmup', daemon=True)
            th.start()
            _logger.info('Warmup de caché disparado en segundo plano (async=%s)', async_enabled)
        else:
            _do_warmup()
            _logger.info('Warmup de caché ejecutado en modo sincrónico')
    except Exception as e:
        _logger.warning('No se pudo iniciar warmup de caché: %s', e, exc_info=True)