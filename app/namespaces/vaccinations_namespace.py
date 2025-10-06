# app/namespaces/vaccinations_namespace.py

from flask import request

from flask_restx import Resource

from flask_jwt_extended import jwt_required

from app.models.vaccinations import Vaccinations

from app.utils.namespace_helpers import create_optimized_namespace

from app.utils.response_handler import APIResponse

from app import db

import logging


logger = logging.getLogger(__name__)


vaccinations_ns = create_optimized_namespace(
    name='vaccinations',
    description='Vacunaciones',
    model_class=Vaccinations,
    path='/vaccinations'
)

# Deshabilitado: CRUD estándar manejado por create_optimized_namespace
# @vaccinations_ns.route('/<int:record_id>')
class VaccinationDetail(Resource):
    @vaccinations_ns.doc('get_vaccination', description='Obtener vacunación por ID')
    @jwt_required()
    def get(self, record_id):
        vaccination = Vaccinations.query.get_or_404(record_id)
        return APIResponse.success(data=vaccination.to_json())

    @vaccinations_ns.doc('update_vaccination', description='Actualizar vacunación')
    @jwt_required()
    def put(self, record_id):
        vaccination = Vaccinations.query.get_or_404(record_id)
        data = vaccinations_ns.payload
        for key, value in data.items():
            setattr(vaccination, key, value)
        db.session.flush()
        db.session.commit()
        db.session.refresh(vaccination)
        return APIResponse.success(data=vaccination.to_json())

    @vaccinations_ns.doc('delete_vaccination', description='Eliminar vacunación')
    @jwt_required()
    def delete(self, record_id):
        vaccination = Vaccinations.query.get_or_404(record_id)
        db.session.delete(vaccination)
        db.session.commit()
        return APIResponse.success(message='Vacunación eliminada')

# Deshabilitado: CRUD estándar manejado por create_optimized_namespace
# @vaccinations_ns.route('')
class VaccinationsList(Resource):
    @vaccinations_ns.doc('get_vaccinations', description='Listar todas las vacunaciones')
    @jwt_required()
    def get(self):
        # Nota: Deshabilitado; esta clase no está registrada (decorador comentado). Se deja paginado por seguridad si se reactivara.
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        query = Vaccinations.query
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [v.to_json() for v in pagination.items]
        return APIResponse.paginated_success(data=items, page=page, limit=int(limit), total_items=pagination.total, message='Vacunaciones obtenidas')

    @vaccinations_ns.doc('create_vaccination', description='Crear nueva vacunación')
    @jwt_required()
    def post(self):
        data = vaccinations_ns.payload
        vaccination = Vaccinations(**data)
        db.session.add(vaccination)
        db.session.flush()
        db.session.commit()
        db.session.refresh(vaccination)
        return APIResponse.success(data=vaccination.to_json(), message='Vacunación creada')
