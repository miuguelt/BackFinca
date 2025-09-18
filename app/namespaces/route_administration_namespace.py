from flask import request
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required
from app.models.route_administration import RouteAdministration
from app.utils.namespace_helpers import create_optimized_namespace
from app.utils.response_handler import APIResponse, ResponseFormatter

# Crear el namespace optimizado para rutas de administración
route_admin_ns = create_optimized_namespace(
    'route-administrations',
    'Rutas de Administración',
    RouteAdministration,
)
# 'Gestión de rutas de administración de medicamentos'  # Removed for consistency

# Modelos para la documentación de Swagger
route_admin_model = route_admin_ns.model('RouteAdministration', {
    'id': fields.Integer(readOnly=True, description='ID único de la ruta de administración'),
    'name': fields.String(required=True, description='Nombre de la ruta de administración', example='Oral'),
    'description': fields.String(description='Descripción de la ruta de administración', example='Administración por vía oral'),
    'status': fields.Boolean(description='Estado activo/inactivo', default=True),
    'created_at': fields.DateTime(readOnly=True, description='Fecha de creación'),
    'updated_at': fields.DateTime(readOnly=True, description='Fecha de última actualización')
})

route_admin_input_model = route_admin_ns.model('RouteAdministrationInput', {
    'name': fields.String(required=True, description='Nombre de la ruta de administración', example='Oral'),
    'description': fields.String(description='Descripción de la ruta de administración', example='Administración por vía oral'),
    'status': fields.Boolean(description='Estado activo/inactivo', default=True)
})

route_admin_update_model = route_admin_ns.model('RouteAdministrationUpdate', {
    'name': fields.String(description='Nombre de la ruta de administración'),
    'description': fields.String(description='Descripción de la ruta de administración'),
    'status': fields.Boolean(description='Estado activo/inactivo')
})

# Los recursos CRUD son creados automáticamente por create_crud_namespace
# Pero podemos agregar recursos personalizados si es necesario

@route_admin_ns.route('/search')
class RouteAdministrationSearch(Resource):
    @jwt_required()
    @route_admin_ns.doc('search_route_administrations')
    # @route_admin_ns.expect(route_admin_ns.parser().add_argument('q', type=str, location='args', help='Término de búsqueda'))
    # @route_admin_ns.marshal_list_with(route_admin_model)
    def get(self):
        """Buscar rutas de administración por nombre o descripción (paginado)"""
        q = request.args.get('q', default='', type=str)
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        try:
            query = RouteAdministration.query.filter(RouteAdministration.status == True)
            if q:
                query = query.filter(
                    (RouteAdministration.name.ilike(f'%{q}%')) |
                    (RouteAdministration.description.ilike(f'%{q}%'))
                )
            pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
            items = [
                (item.to_namespace_dict() if hasattr(item, 'to_namespace_dict') else {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'status': item.status,
                    'created_at': getattr(item, 'created_at', None),
                    'updated_at': getattr(item, 'updated_at', None)
                }) for item in pagination.items
            ]
            sanitized = ResponseFormatter.sanitize_for_frontend(items)
            return APIResponse.paginated_success(
                data=sanitized,
                page=page,
                limit=int(limit),
                total_items=pagination.total,
                message='Resultados de búsqueda obtenidos'
            )
        except Exception as e:
            return APIResponse.error('Error al buscar rutas de administración', details={'error': str(e)}, status_code=500)

@route_admin_ns.route('/active')
class ActiveRouteAdministrations(Resource):
    @jwt_required()
    @route_admin_ns.doc('get_active_route_administrations')
    # @route_admin_ns.marshal_list_with(route_admin_model)
    def get(self):
        """Obtener rutas de administración activas (paginado)"""
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        try:
            query = RouteAdministration.query.filter_by(status=True)
            pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
            items = [
                (item.to_namespace_dict() if hasattr(item, 'to_namespace_dict') else {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'status': item.status,
                    'created_at': getattr(item, 'created_at', None),
                    'updated_at': getattr(item, 'updated_at', None)
                }) for item in pagination.items
            ]
            sanitized = ResponseFormatter.sanitize_for_frontend(items)
            return APIResponse.paginated_success(
                data=sanitized,
                page=page,
                limit=int(limit),
                total_items=pagination.total,
                message='Rutas activas obtenidas'
            )
        except Exception as e:
            return APIResponse.error('Error al obtener rutas activas', details={'error': str(e)}, status_code=500)
