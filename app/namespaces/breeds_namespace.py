# app/namespaces/breeds_namespace.py

from flask import request

from flask_restx import Resource

from flask_jwt_extended import jwt_required

from app.models.breeds import Breeds

from app.utils.namespace_helpers import create_optimized_namespace

from app.utils.response_handler import APIResponse, ResponseFormatter

from app import db

import logging


logger = logging.getLogger(__name__)


breeds_ns = create_optimized_namespace(
    name='breeds',
    description='Operaciones relacionadas con razas',
    model_class=Breeds,
    path='/breeds'
)

# Deshabilitado: CRUD estándar manejado por create_optimized_namespace
# @breeds_ns.route('/<int:record_id>')
class BreedDetail(Resource):
    @breeds_ns.doc('get_breed', description='Obtener raza por ID')
    @jwt_required()
    def get(self, record_id):
        breed = Breeds.query.get_or_404(record_id)
        return APIResponse.success(data=breed.to_json())

    @breeds_ns.doc('update_breed', description='Actualizar raza')
    @jwt_required()
    def put(self, record_id):
        breed = Breeds.query.get_or_404(record_id)
        data = breeds_ns.payload
        for key, value in data.items():
            setattr(breed, key, value)
        db.session.commit()
        return APIResponse.success(data=breed.to_json())

    @breeds_ns.doc('delete_breed', description='Eliminar raza')
    @jwt_required()
    def delete(self, record_id):
        breed = Breeds.query.get_or_404(record_id)
        db.session.delete(breed)
        db.session.commit()
        return APIResponse.success(message='Raza eliminada')


@breeds_ns.route('/by-species/<int:species_id>')
class BreedsBySpecies(Resource):
    @breeds_ns.doc('get_breeds_by_species', description='Obtener razas por especie (paginado)')
    @jwt_required()
    def get(self, species_id):
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        query = Breeds.query.filter_by(species_id=species_id)
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [
            (b.to_namespace_dict() if hasattr(b, 'to_namespace_dict') else b.to_json()) for b in pagination.items
        ]
        sanitized = ResponseFormatter.sanitize_for_frontend(items)
        return APIResponse.paginated_success(
            data=sanitized,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Razas por especie obtenidas'
        )

# Deshabilitado: CRUD estándar manejado por create_optimized_namespace
# @breeds_ns.route('')
class BreedsList(Resource):
    @breeds_ns.doc('get_breeds', description='Listar todas las razas')
    @jwt_required()
    def get(self):
        # Nota: Deshabilitado; esta clase no está registrada (decorador comentado). Se deja paginado por seguridad si se reactivara.
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        query = Breeds.query
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [
            (b.to_namespace_dict() if hasattr(b, 'to_namespace_dict') else b.to_json()) for b in pagination.items
        ]
        sanitized = ResponseFormatter.sanitize_for_frontend(items)
        return APIResponse.paginated_success(
            data=sanitized,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Razas obtenidas'
        )

    @breeds_ns.doc('create_breed', description='Crear nueva raza')
    @jwt_required()
    def post(self):
        data = breeds_ns.payload
        breed = Breeds(**data)
        db.session.add(breed)
        db.session.commit()
        return APIResponse.success(data=breed.to_json(), message='Raza creada')
