from flask_restx import Resource, Namespace, fields
import jwt
from flask import request, jsonify
from datetime import datetime
from app.models.animalFields import AnimalFields
from app.models.animals import Animals  # Corregido: Animals en lugar de Animal
from app.models.fields import Fields  # Corregido: Fields en lugar de Field
from app import db
from app.utils.namespace_helpers import create_optimized_namespace, _cache_clear
from app.utils.response_handler import APIResponse

animal_fields_ns = create_optimized_namespace(
    name='AnimalFields',
    description='Operaciones CRUD para campos de animales',
    model_class=AnimalFields,
    path='/animal-fields'
)

model_for_update = animal_fields_ns.model('AnimalFieldUpdate', {
    'value': fields.String(required=True),
    'field_id': fields.Integer(required=True),
    'animal_id': fields.Integer(required=True)
})

model_for_partial_update = animal_fields_ns.model('AnimalFieldPartialUpdate', {
    'value': fields.String,
    'field_id': fields.Integer,
    'animal_id': fields.Integer
})

model_for_create = animal_fields_ns.model('AnimalFieldCreate', {
    'value': fields.String(required=True),
    'field_id': fields.Integer(required=True),
    'animal_id': fields.Integer(required=True)
})

model_for_list = animal_fields_ns.model('AnimalFieldsList', {
    'id': fields.Integer(readonly=True),
    'value': fields.String,
    'field_id': fields.Integer,
    'animal_id': fields.Integer,
    'created_at': fields.DateTime,
    'updated_at': fields.DateTime
})

class AnimalFieldsDetail(Resource):
    @animal_fields_ns.doc(security=[{'Bearer': []}])
    @animal_fields_ns.marshal_with(model_for_update, code=200, description='Campo de animal obtenido exitosamente')
    @animal_fields_ns.expect(model_for_update)
    def get(self, record_id):
        """Obtener un campo de animal específico por ID"""
        try:
            record = AnimalFields.query.get_or_404(record_id)
            return APIResponse.success(record, animal_fields_ns)
        except Exception as e:
            return APIResponse.error(f'Error al obtener campo de animal: {str(e)}', 404)

    @animal_fields_ns.doc(security=[{'Bearer': []}])
    @animal_fields_ns.marshal_with(model_for_update, code=200, description='Campo de animal actualizado exitosamente')
    @animal_fields_ns.expect(model_for_update)
    def put(self, record_id):
        """Actualizar completamente un campo de animal por ID"""
        try:
            data = request.get_json() or {}
            # Consulta directa a BD (sin cache)
            record = AnimalFields.query.get_or_404(record_id)
            for attr, value in data.items():
                if hasattr(record, attr):
                    setattr(record, attr, value)
            record.updated_at = datetime.utcnow()
            db.session.flush()
            db.session.commit()
            db.session.refresh(record)

            # Invalidar cache INMEDIATAMENTE después de sincronización
            _cache_clear('AnimalFields')

            # Respuesta con datos sincronizados desde BD
            return APIResponse.success(record, animal_fields_ns)
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(f'Error al actualizar campo de animal: {str(e)}', 400)

    @animal_fields_ns.doc(security=[{'Bearer': []}])
    @animal_fields_ns.response(204, 'Campo de animal eliminado exitosamente')
    def delete(self, record_id):
        """Eliminar permanentemente un campo de animal por ID"""
        try:
            # Consulta directa a BD (sin cache)
            record = AnimalFields.query.get_or_404(record_id)
            db.session.delete(record)
            db.session.commit()

            # Invalidar cache INMEDIATAMENTE después de commit exitoso
            _cache_clear('AnimalFields')

            # Respuesta rápida HTTP 204 (sin contenido)
            return '', 204
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(f'Error al eliminar campo de animal: {str(e)}', 400)

    @animal_fields_ns.doc(security=[{'Bearer': []}])
    @animal_fields_ns.marshal_with(model_for_update, code=200, description='Campo de animal actualizado parcialmente exitosamente')
    @animal_fields_ns.expect(model_for_partial_update)
    def patch(self, record_id):
        """Actualizar parcialmente un campo de animal por ID"""
        try:
            data = request.get_json() or {}
            if not data:
                return APIResponse.error('No se proporcionaron datos para actualizar', 404)
            # Consulta directa a BD (sin cache)
            record = AnimalFields.query.get_or_404(record_id)
            for attr, value in data.items():
                if hasattr(record, attr):
                    setattr(record, attr, value)
            record.updated_at = datetime.utcnow()
            db.session.flush()
            db.session.commit()
            db.session.refresh(record)

            # Invalidar cache INMEDIATAMENTE después de sincronización
            _cache_clear('AnimalFields')

            # Respuesta con datos sincronizados desde BD
            return APIResponse.success(record, animal_fields_ns)
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(f'Error al actualizar parcialmente campo de animal: {str(e)}', 400)

# Delegado a create_optimized_namespace (evita duplicar recursos y posibles consultas pesadas)
# animal_fields_ns.add_resource(AnimalFieldsDetail, '/<int:record_id>')
# animal_fields_ns.add_resource(AnimalFieldsList, '/')

class AnimalFieldsList(Resource):
    @animal_fields_ns.doc(security=[{'Bearer': []}])
    @animal_fields_ns.marshal_list_with(model_for_list)
    @animal_fields_ns.expect(model_for_list, validate=True)
    def get(self):
        """Listar todos los campos de animales con paginación y búsqueda"""
        try:
            page = request.args.get('page', default=1, type=int) or 1
            limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
            search = request.args.get('search', '')

            query = AnimalFields.query
            if search:
                query = query.filter(
                    AnimalFields.value.ilike(f'%{search}%')
                )

            pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
            return APIResponse.success({
                'items': pagination.items,
                'total': pagination.total,
                'pages': pagination.pages,
                'page': page,
                'per_page': int(limit)
            }, animal_fields_ns)
        except Exception as e:
            return APIResponse.error(f'Error al listar campos de animales: {str(e)}', 500)

    @animal_fields_ns.doc(security=[{'Bearer': []}])
    @animal_fields_ns.marshal_with(model_for_create, code=201, description='Campo de animal creado exitosamente')
    @animal_fields_ns.expect(model_for_create, validate=True)
    def post(self):
        """Crear un nuevo campo de animal"""
        try:
            data = request.get_json()
            field_id = data.get('field_id')
            animal_id = data.get('animal_id')
            value = data.get('value')

            if not Fields.query.get(field_id):  # Corregido: Fields en lugar de Field
                return APIResponse.error('Campo no encontrado', 404)
            if not Animals.query.get(animal_id):
                return APIResponse.error('Animal no encontrado', 404)

            existing = AnimalFields.query.filter_by(field_id=field_id, animal_id=animal_id).first()
            if existing:
                return APIResponse.error('Registro duplicado ya existe', 400)

            record = AnimalFields(
                value=value,
                field_id=field_id,
                animal_id=animal_id
            )
            db.session.add(record)
            db.session.flush()
            db.session.commit()
            db.session.refresh(record)

            # Invalidar cache INMEDIATAMENTE después de sincronización
            _cache_clear('AnimalFields')

            # Respuesta rápida con datos desde BD (sin cache)
            return APIResponse.success(record, animal_fields_ns), 201
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(f'Error al crear campo de animal: {str(e)}', 400)
