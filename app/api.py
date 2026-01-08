from __future__ import annotations

import logging
import time
import importlib
import pkgutil
import pathlib
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file, render_template
from flask_restx import Api
from sqlalchemy import text

from . import db
from .utils.response_handler import APIResponse


def register_api(app, limiter=None):
    """Registrar Blueprint '/api/v1', configurar Flask-RESTX y exponer endpoints utilitarios.

    - Registra todos los namespaces existentes
    - Aplica rate limits específicos al namespace de autenticación (si hay limiter)
    - Expone endpoints: /api/v1/health, /api/v1/docs/schema, /api/v1/docs/examples
    """
    logger = logging.getLogger(__name__)

    # Crear el blueprint para la API
    api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


    access_cookie_name = app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token_cookie')
    refresh_cookie_name = app.config.get('JWT_REFRESH_COOKIE_NAME', 'refresh_token_cookie')
    csrf_access_cookie_name = app.config.get('JWT_ACCESS_CSRF_COOKIE_NAME', 'csrf_access_token')
    csrf_refresh_cookie_name = app.config.get('JWT_REFRESH_CSRF_COOKIE_NAME', 'csrf_refresh_token')

    from collections import OrderedDict
    
    authorizations = OrderedDict()
    authorizations['Bearer'] = {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'JWT token. Formato: Bearer <token>'
    }
    authorizations['Cookie'] = {
        'type': 'apiKey',
        'in': 'cookie',
        'name': access_cookie_name,
        'description': 'JWT token en cookie (autenticación automática)'
    }

    # Configurar Flask-RESTX con optimizaciones JSON y documentación
    api = Api(
        api_bp,
        default_mediatype='application/json',
        version='1.0',
        title='Finca Villa Luz API',
        description='''**API Optimizada para Finca Villa Luz**\n\nUna API RESTful para la gestión integral de ganado. Todos los endpoints devuelven respuestas en formato JSON estandarizado.\n\n**Notas de Inicio Rápido:**\n1.  **Autenticación**:\n    -   Usa el endpoint `/auth/login` para obtener tus tokens.\n    -   Usuario administrador por defecto: `identification=99999999`, `password=password123`.\n    -   La API utiliza JWT, que se puede enviar como `Bearer` token en el encabezado `Authorization` o a través de cookies seguras (HttpOnly).\n\n2.  **Endpoints**:\n    -   La mayoría de los recursos (animales, usuarios, etc.) siguen un patrón CRUD estándar.\n    -   Endpoints de analítica (`/analytics`) y seguridad (`/security`) ofrecen datos agregados.\n\n3.  **Respuestas JSON**:\n    -   Las respuestas exitosas (`200 OK`, `201CREATED`) siguen la estructura: `{ "success": true, "message": "...", "data": { ... } }`.\n    -   Las respuestas de error (`4xx`, `5xx`) siguen la estructura: `{ "success": false, "error": "...", "message": "...", "details": { ... } }`.\n\n**Guía para Frontend**: Consulta la guía de uso con ejemplos en `/api/v1/docs/guia-frontend`.''',
        doc='/docs/',
        contact='Finca Villa Luz',
        contact_email='info@fincavillaluz.com',
        license='MIT',
        license_url='https://opensource.org/licenses/MIT',
        authorizations=authorizations,
        security=['Bearer', 'Cookie'],
        validate=False,
        ordered=True,
        catch_all_404s=True,
    )

    # UI de documentación personalizada con enlace visible a la guía
    @api.documentation
    def custom_swagger_ui():
        return render_template(
            'swagger_ui_custom.html',
            title=api.title,
            specs_url=api.specs_url,
            cookie_config={
                'access': access_cookie_name,
                'refresh': refresh_cookie_name,
                'csrf_access': csrf_access_cookie_name,
                'csrf_refresh': csrf_refresh_cookie_name,
            },
        )

    # Namespaces
    from .namespaces.auth_namespace import auth_ns, set_limiter as set_auth_limiter
    from .namespaces.users_namespace import users_ns, set_limiter as set_users_limiter
    from .namespaces.animals_namespace import animals_ns
    from .namespaces.analytics_namespace import analytics_ns
    from .namespaces.security_namespace import security_ns
    from .namespaces.species_namespace import species_ns
    from .namespaces.breeds_namespace import breeds_ns
    from .namespaces.control_namespace import control_ns
    from .namespaces.fields_namespace import fields_ns
    from .namespaces.diseases_namespace import diseases_ns
    from .namespaces.genetic_improvements_namespace import genetic_improvements_ns
    from .namespaces.food_types_namespace import food_types_ns
    from .namespaces.treatments_namespace import treatments_ns
    from .namespaces.vaccinations_namespace import vaccinations_ns
    from .namespaces.vaccines_namespace import vaccines_ns
    from .namespaces.medications_namespace import medications_ns
    from .namespaces.route_administration_namespace import route_admin_ns
    from .namespaces.animal_diseases_namespace import animal_diseases_ns
    from .namespaces.animal_fields_namespace import animal_fields_ns
    from .namespaces.treatment_medications_namespace import treatment_medications_ns
    from .namespaces.treatment_vaccines_namespace import treatment_vaccines_ns
    from .namespaces.user_preferences_namespace import prefs_ns
    from .namespaces.navigation_namespace import nav_ns
    from .namespaces.animal_images_namespace import animal_images_ns
    from .namespaces.activity_namespace import activity_ns, set_limiter as set_activity_limiter

    # Aplicar rate limits específicos a endpoints de autenticación (solo si hay limiter)
    try:
        if app.config.get('RATE_LIMIT_ENABLED', True) and limiter:
            set_auth_limiter(limiter)
            try:
                set_users_limiter(limiter)
            except Exception:
                logging.getLogger(__name__).exception('No se pudo aplicar rate limiting a users_namespace')
            try:
                set_activity_limiter(limiter)
            except Exception:
                logging.getLogger(__name__).exception('No se pudo aplicar rate limiting a activity_namespace')
        else:
            logging.getLogger(__name__).info('Rate limiting no aplicado (deshabilitado o sin limiter)')
    except Exception:
        logging.getLogger(__name__).exception('No se pudo aplicar rate limiting a auth/users namespaces')

    # Registrar namespaces
    api.add_namespace(auth_ns)
    api.add_namespace(users_ns)
    api.add_namespace(animals_ns)
    api.add_namespace(analytics_ns)
    api.add_namespace(security_ns)
    api.add_namespace(species_ns)
    api.add_namespace(breeds_ns)
    api.add_namespace(control_ns)
    api.add_namespace(fields_ns)
    api.add_namespace(diseases_ns)
    api.add_namespace(genetic_improvements_ns)
    api.add_namespace(food_types_ns)
    api.add_namespace(treatments_ns)
    api.add_namespace(vaccinations_ns)
    api.add_namespace(vaccines_ns)
    api.add_namespace(medications_ns)
    api.add_namespace(route_admin_ns)
    api.add_namespace(animal_diseases_ns)
    api.add_namespace(animal_fields_ns)
    api.add_namespace(treatment_medications_ns)
    api.add_namespace(treatment_vaccines_ns)
    api.add_namespace(prefs_ns)
    api.add_namespace(nav_ns)
    api.add_namespace(animal_images_ns)
    api.add_namespace(activity_ns)

    # Endpoint de health check público y documentado en la guía: /api/v1/health
    @api_bp.route('/health', methods=['GET', 'OPTIONS'])
    def api_health():
        # Permitir preflight CORS
        if request.method == 'OPTIONS':
            return '', 200
        try:
            # Verificar conexión simple a la base de datos
            db.session.execute(text('SELECT 1'))
            db_status = 'healthy'
            status_code = 200
        except Exception as e:  # pragma: no cover - comportamiento en fallos
            db_status = f'unhealthy: {str(e)}'
            status_code = 503

        payload = {
            'success': True if status_code == 200 else False,
            'status': 'healthy' if status_code == 200 else 'unhealthy',
            'services': {
                'database': db_status
            },
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'uptime_seconds': time.time() - app.config.get('START_TIME', time.time()),
            'version': app.config.get('APP_VERSION', app.config.get('VERSION', '1.0.0')),
        }
        return jsonify(payload), status_code

    # ==============================================================
    # Dynamic schema/metadata endpoint for documentation/templates
    # ==============================================================
    @api_bp.route('/docs/schema', methods=['GET'])
    def docs_schema():
        """Devolver metadatos dinámicos enriquecidos de modelos y namespaces."""
        # Intentar importar todas las clases de modelo registradas como subclases de BaseModel
        imported_any = False
        try:
            # Intentar importar como paquete normal
            model_pkg = 'app.models'
            pkg = importlib.import_module(model_pkg)
            for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__):
                try:
                    importlib.import_module(f"{model_pkg}.{name}")
                    imported_any = True
                except Exception:
                    logging.getLogger(__name__).debug('No se pudo importar modelo: %s', name, exc_info=True)
        except Exception:
            logging.getLogger(__name__).debug('app.models no es un paquete importable; se usará escaneo de archivos', exc_info=True)

        if not imported_any:
            # Fallback: escanear el directorio app/models y importar por nombre de archivo
            try:
                base_dir = pathlib.Path(__file__).parent
                models_dir = base_dir / 'models'
                if models_dir.exists() and models_dir.is_dir():
                    for p in models_dir.iterdir():
                        if p.is_file() and p.suffix == '.py' and p.name != '__init__.py':
                            mod_name = p.stem
                            try:
                                importlib.import_module(f"app.models.{mod_name}")
                                imported_any = True
                            except Exception:
                                logging.getLogger(__name__).debug('No se pudo importar modelo desde archivo: %s', p.name, exc_info=True)
            except Exception:
                logging.getLogger(__name__).warning('No se pudo escanear app/models para importar módulos', exc_info=True)

        # Always use BaseModel.__subclasses__() to populate model_classes
        model_classes = []
        try:
            from app.models.base_model import BaseModel
            for s in BaseModel.__subclasses__():
                model_classes.append(s)
        except Exception as e:
            logging.getLogger(__name__).warning('Error listando modelos: %s', e)

        def _example_value(col_type_str: str):
            t = col_type_str.lower()
            if 'int' in t:
                return 123
            if 'bool' in t:
                return True
            if 'date' in t:
                return '2025-01-01'
            if 'enum' in t:
                return 'VALUE'
            if 'float' in t or 'numeric' in t or 'dec' in t:
                return 1.23
            return 'texto'

        def serialize_model(cls):
            data = {
                'model': cls.__name__,
                'table': getattr(cls, '__tablename__', None),
                'fields': [],
                'filterable': getattr(cls, '_filterable_fields', []),
                'searchable': getattr(cls, '_searchable_fields', []),
                'sortable': getattr(cls, '_sortable_fields', []),
                'required': getattr(cls, '_required_fields', []),
                'unique': getattr(cls, '_unique_fields', []),
                'enums': {},
                'relations': {},
                'examples': {},
            }
            create_example = {}
            update_example = {}
            try:
                # Helper to sanitize values that are not JSON serializable by default
                def _sanitize_value(v):
                    import datetime as _dt
                    import enum as _enum

                    if v is None:
                        return None
                    if isinstance(v, _enum.Enum):
                        try:
                            return v.value
                        except Exception:
                            return str(v)
                    if isinstance(v, (_dt.datetime, _dt.date)):
                        try:
                            return v.isoformat()
                        except Exception:
                            return str(v)
                    if callable(v):
                        try:
                            return str(v)
                        except Exception:
                            return None
                    if isinstance(v, dict):
                        return {k: _sanitize_value(val) for k, val in v.items()}
                    if isinstance(v, (list, tuple, set)):
                        return [_sanitize_value(x) for x in v]
                    return v

                for col in cls.__table__.columns:  # type: ignore[attr-defined]
                    col_type = str(col.type)
                    raw_default = getattr(col.default, 'arg', None) if col.default is not None else None
                    try:
                        if callable(raw_default):
                            default_val = str(raw_default)
                        else:
                            default_val = _sanitize_value(raw_default)
                    except Exception:
                        default_val = None
                    f = {
                        'name': col.name,
                        'type': col_type,
                        'nullable': col.nullable,
                        'primary_key': col.primary_key,
                        'default': default_val,
                    }
                    data['fields'].append(f)
                    if not col.primary_key and col.name not in ('created_at', 'updated_at'):
                        if col.name in data['required']:
                            create_example[col.name] = _example_value(col_type)
                        else:
                            if col.name in getattr(cls, '_enum_fields', {}):
                                create_example[col.name] = 'ENUM_VALUE'
                            else:
                                create_example[col.name] = _example_value(col_type)
                        if len(update_example) < 3:
                            update_example[col.name] = _example_value(col_type)
                for fname, enum_cls in getattr(cls, '_enum_fields', {}).items():
                    try:
                        values = [e.value for e in enum_cls]
                        data['enums'][fname] = values
                        if fname in create_example:
                            create_example[fname] = values[0] if values else None
                        if fname in update_example:
                            update_example[fname] = values[-1] if values else None
                    except Exception:
                        pass
                for rel_name, rel_cfg in getattr(cls, '_namespace_relations', {}).items():
                    data['relations'][rel_name] = {
                        'fields': rel_cfg.get('fields'),
                        'depth': rel_cfg.get('depth', 1),
                    }
                try:
                    create_example = {k: _sanitize_value(v) for k, v in create_example.items()}
                    update_example = {k: _sanitize_value(v) for k, v in update_example.items()}
                except Exception:
                    pass
                data['examples'] = {
                    'create': create_example,
                    'update': update_example,
                }
            except Exception as e:  # pragma: no cover - fallback ante errores
                logging.getLogger(__name__).warning('Fallo serializando %s: %s', getattr(cls, '__name__', cls), e)
                return {
                    'model': getattr(cls, '__name__', str(cls)),
                    'table': getattr(cls, '__tablename__', None),
                    'fields': [],
                    'filterable': getattr(cls, '_filterable_fields', []),
                    'searchable': getattr(cls, '_searchable_fields', []),
                    'sortable': getattr(cls, '_sortable_fields', []),
                    'required': getattr(cls, '_required_fields', []),
                    'unique': getattr(cls, '_unique_fields', []),
                    'enums': {},
                    'relations': {},
                    'examples': {'create': {}, 'update': {}},
                }
            return data

        payload = {
            'success': True,
            'message': 'Esquema dinámico generado',
            'data': {
                'models': [serialize_model(m) for m in model_classes],
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            },
            'status_code': 200,
        }
        return jsonify(payload), 200

    @api_bp.route('/docs/examples', methods=['GET'])
    def docs_examples():
        """Construye ejemplos simples de requests basados en /docs/schema."""
        schema_resp = docs_schema()[0].json
        examples = []
        for m in schema_resp['data']['models']:
            model = m.get('model')
            create_ex = m.get('examples', {}).get('create', {}) or {}
            required = m.get('required', []) or []
            enums = m.get('enums', {}) or {}
            field_types = {f['name']: f.get('type', '').lower() for f in (m.get('fields') or [])}
            for req in required:
                if req not in create_ex or create_ex.get(req) in (None, ''):
                    if req in enums and enums[req]:
                        create_ex[req] = enums[req][0]
                    else:
                        ftype = field_types.get(req, '')
                        if 'date' in ftype:
                            create_ex[req] = '2025-01-01'
                        elif 'int' in ftype:
                            create_ex[req] = 1
                        elif 'bool' in ftype:
                            create_ex[req] = True
                        else:
                            create_ex[req] = 'example'
            for en_field, vals in enums.items():
                if en_field in create_ex and create_ex[en_field] not in vals:
                    create_ex[en_field] = vals[0] if vals else create_ex[en_field]

            table = m.get('table') or (model or '').lower()
            if table:
                endpoint_base = table if str(table).endswith('s') else f"{table}s"
            else:
                endpoint_base = (model or '').lower() + 's'

            examples.append({
                'model': model,
                'create_request': create_ex,
                'create_endpoint': f"/api/v1/{endpoint_base}/",
                'list_example': f"GET /api/v1/{endpoint_base}/?page=1&limit=10",
                'filters_available': m.get('filterable', []),
                'searchable': m.get('searchable', []),
                'sortable': m.get('sortable', []),
            })
        return jsonify({
            'success': True,
            'message': 'Ejemplos generados',
            'data': {'examples': examples},
            'status_code': 200,
        }), 200

    # Nueva ruta pública para la guía del frontend
    @api_bp.route('/docs/guia-frontend', methods=['GET'])
    def docs_frontend_guide():
        """Servir la guía de uso del frontend (Markdown)."""
        try:
            md_path = pathlib.Path(__file__).parents[1] / 'docs' / 'api-usage-guia-frontend.md'
            if not md_path.exists():
                fallback = (
                    "# Guía Frontend\n\n"
                    "No se encontró el archivo de guía en el servidor (docs/api-usage-guia-frontend.md).\n\n"
                    "Esta es una versión mínima. Una vez que el archivo exista, esta ruta lo servirá automáticamente.\n"
                )
                return fallback, 200, {'Content-Type': 'text/markdown; charset=utf-8'}
            return send_file(str(md_path), mimetype='text/markdown; charset=utf-8')
        except Exception as e:
            return jsonify({'success': False, 'message': 'Error sirviendo la guía', 'details': str(e)}), 500

    # Nueva vista HTML para renderizar la guía con estilos
    @api_bp.route('/docs/guia-frontend-html', methods=['GET'])
    def docs_frontend_guide_html():
        return render_template('guia_frontend.html', title='Guía Frontend')

    # Endpoint público raíz de confirmación dentro de /api/v1
    @api_bp.route('/', methods=['GET', 'OPTIONS'])
    def api_root_confirm():
        # Permitir preflight CORS
        if request.method == 'OPTIONS':
            return '', 200
        return APIResponse.success(
            message='Bienvenido al backend de la Finca Villaluz',
            data={'public': True, 'endpoint': '/api/v1/'}
        )

    # Registrar el blueprint
    app.register_blueprint(api_bp)

    return api
