# app/namespaces/vaccines_namespace.py

from flask import request
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import selectinload, load_only

from app.models.vaccines import Vaccines
from app.utils.namespace_helpers import create_optimized_namespace
from app.utils.response_handler import APIResponse, ResponseFormatter

# Namespace con CRUD estándar optimizado (listado, create, retrieve, update, delete)
vaccines_ns = create_optimized_namespace(
    name='vaccines',
    description='Vacunas disponibles',
    model_class=Vaccines,
    path='/vaccines'
)

# Modelo de documentación (para Swagger)
vaccine_model = vaccines_ns.model('Vaccine', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True),
    'description': fields.String(),
    'manufacturer': fields.String(),
    'route_administration_id': fields.Integer(),
    'created_at': fields.DateTime(),
    'updated_at': fields.DateTime()
})


@vaccines_ns.route('/with-route-administration')
class VaccinesWithRouteAdmin(Resource):
    @jwt_required()
    @vaccines_ns.doc('get_vaccines_with_route_administration', description='Listado paginado de vacunas incluyendo la relación de ruta de administración. Ejemplos: ?page=1&limit=50&search=anti&fields=id,name,manufacturer', params={'page': 'Página (int)', 'limit': 'Elementos por página (int)', 'search': 'Texto de búsqueda simple por nombre', 'fields': 'Lista separada por comas de campos a incluir (ej: id,name,manufacturer)'})
    def get(self):
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        search = request.args.get('search')
        fields_param = request.args.get('fields')
        selected = [f.strip() for f in fields_param.split(',') if f.strip()] if fields_param else None

        # Construir query con proyección de columnas si se solicitaron
        query = Vaccines.query
        if selected:
            allowed = getattr(Vaccines, '_namespace_fields', [])
            col_fields = [f for f in selected if f in allowed]
            if col_fields:
                query = query.options(load_only(*[getattr(Vaccines, f) for f in col_fields if hasattr(Vaccines, f)]))

        # Precarga eficiente de la relación requerida por este endpoint
        query = query.options(selectinload(Vaccines.route_administration_rel))

        if search:
            query = query.filter(Vaccines.name.ilike(f'%{search}%'))

        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = []
        for v in pagination.items:
            # Evitar cargar relaciones pesadas (vaccinations/diseases) y solo adjuntar la ruta precargada
            base = v.to_namespace_dict(include_relations=False, fields=selected) if hasattr(v, 'to_namespace_dict') else {
                'id': v.id,
                'name': v.name,
                'description': getattr(v, 'description', None),
                'manufacturer': getattr(v, 'manufacturer', None),
                'route_administration_id': v.route_administration_id,
                'created_at': getattr(v, 'created_at', None),
                'updated_at': getattr(v, 'updated_at', None)
            }

            # Adjuntar relación de ruta de administración con proyección mínima
            route = getattr(v, 'route_administration_rel', None)
            if route is not None:
                base['route_administration'] = {
                    'id': getattr(route, 'id', None),
                    'name': getattr(route, 'name', None)
                }
            else:
                base['route_administration'] = None

            items.append(base)

        sanitized = ResponseFormatter.sanitize_for_frontend(items)
        return APIResponse.paginated_success(
            data=sanitized,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Vacunas con ruta obtenidas'
        )


@vaccines_ns.route('/by-route/<int:route_id>')
class VaccinesByRoute(Resource):
    @jwt_required()
    @vaccines_ns.doc('get_vaccines_by_route', description='Listado paginado de vacunas filtradas por ruta de administración. Ejemplos: ?page=1&limit=50&fields=id,name,route_administration_id', params={'route_id': 'ID de la ruta de administración (path)', 'page': 'Página (int)', 'limit': 'Elementos por página (int)', 'search': 'Texto de búsqueda por nombre', 'fields': 'Lista separada por comas de campos a incluir'})
    def get(self, route_id: int):
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        search = request.args.get('search')
        fields_param = request.args.get('fields')
        selected = [f.strip() for f in fields_param.split(',') if f.strip()] if fields_param else None

        query = Vaccines.query.filter_by(route_administration_id=route_id)

        # Proyección de columnas para reducir I/O
        if selected:
            allowed = getattr(Vaccines, '_namespace_fields', [])
            col_fields = [f for f in selected if f in allowed]
            if col_fields:
                query = query.options(load_only(*[getattr(Vaccines, f) for f in col_fields if hasattr(Vaccines, f)]))

        if search:
            query = query.filter(Vaccines.name.ilike(f'%{search}%'))

        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = []
        for v in pagination.items:
            if hasattr(v, 'to_namespace_dict'):
                data = v.to_namespace_dict(fields=selected)
            else:
                base = {
                    'id': v.id,
                    'name': v.name,
                    'description': getattr(v, 'description', None),
                    'manufacturer': getattr(v, 'manufacturer', None),
                    'route_administration_id': v.route_administration_id,
                    'created_at': getattr(v, 'created_at', None),
                    'updated_at': getattr(v, 'updated_at', None)
                }
                data = {k: base[k] for k in (selected or base.keys()) if k in base}
            items.append(data)

        sanitized = ResponseFormatter.sanitize_for_frontend(items)
        return APIResponse.paginated_success(
            data=sanitized,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Vacunas por ruta obtenidas'
        )
