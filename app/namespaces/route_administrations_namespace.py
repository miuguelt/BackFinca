from flask_restx import Resource, Namespace
from flask import request
from flask_jwt_extended import jwt_required
from app.models.route_administration import RouteAdministration
from app.utils.namespace_helpers import create_optimized_namespace
from app.utils.response_handler import APIResponse
from app import db
import logging

logger = logging.getLogger(__name__)

route_administrations_ns = create_optimized_namespace(
    name='route-administrations',
    description='Gestión de rutas de administración',
    model_class=RouteAdministration,
    path='/route-administrations'
)

# Deshabilitado: rutas duplicadas manejadas por create_optimized_namespace
# @route_administrations_ns.route('/<int:record_id>')
class RouteAdministrationDetail(Resource):
    @route_administrations_ns.doc('get_route_administration')
    @jwt_required()
    def get(self, record_id):
        route = RouteAdministration.query.get_or_404(record_id)
        return APIResponse.success(data=route.to_dict())

    @route_administrations_ns.doc('update_route_administration')
    @jwt_required()
    def put(self, record_id):
        route = RouteAdministration.query.get_or_404(record_id)
        data = route_administrations_ns.payload
        for key, value in data.items():
            setattr(route, key, value)
        db.session.flush()
        db.session.commit()
        db.session.refresh(route)
        return APIResponse.success(data=route.to_dict())

    @route_administrations_ns.doc('delete_route_administration')
    @jwt_required()
    def delete(self, record_id):
        route = RouteAdministration.query.get_or_404(record_id)
        db.session.delete(route)
        db.session.commit()
        return APIResponse.success(message='Ruta de administración eliminada')

# Deshabilitado: rutas duplicadas manejadas por create_optimized_namespace
# @route_administrations_ns.route('')
class RouteAdministrationsList(Resource):
    @route_administrations_ns.doc('get_route_administrations')
    @jwt_required()
    def get(self):
        # Nota: Deshabilitado; esta clase no está registrada (decorador comentado). Se deja paginado por seguridad si se reactivara.
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        query = RouteAdministration.query
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [(r.to_namespace_dict() if hasattr(r, 'to_namespace_dict') else r.to_dict()) for r in pagination.items]
        return APIResponse.paginated_success(data=items, page=page, limit=int(limit), total_items=pagination.total, message='Rutas de administración obtenidas')

    @route_administrations_ns.doc('create_route_administration')
    @jwt_required()
    def post(self):
        data = route_administrations_ns.payload
        route = RouteAdministration(**data)
        db.session.add(route)
        db.session.flush()
        db.session.commit()
        db.session.refresh(route)
        return APIResponse.success(data=route.to_dict(), message='Ruta de administración creada')