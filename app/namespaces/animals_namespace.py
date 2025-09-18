from flask import request
from flask_restx import Resource, Namespace, fields
import sqlalchemy as sa
from sqlalchemy import and_
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity

# Asumir que animal_model está definido en modelos o utils
from app.models.animals import Animals
from app.utils.response_handler import APIResponse
from app.utils.namespace_helpers import create_optimized_namespace

animals_ns = create_optimized_namespace(
    name='animals',
    description='Animales operations',
    model_class=Animals,
    path='/animals'
)

animal_model = animals_ns.model('Animal', {
    'record': fields.String(required=True),
    'sex': fields.String(required=True),
    'birth_date': fields.Date(required=True),
    'weight': fields.Float(required=True),
    'status': fields.String(default='active'),
    'breeds_id': fields.Integer(required=True),
    # Agregar otros campos según el modelo
})

# Deshabilitado: CRUD estándar manejado por create_optimized_namespace
# @animals_ns.route('/')
class AnimalsList(Resource):
    @jwt_required()
    def get(self):
        try:
            page = request.args.get('page', default=1, type=int) or 1
            limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
            search = request.args.get('search', '')
            
            query = Animals.query
            
            if search:
                query = query.filter(Animals.record.ilike(f'%{search}%'))
            
            items = query.paginate(page=page, per_page=int(limit), error_out=False)
            
            return APIResponse.success(
                data={
                    'items': [item.to_namespace_dict() for item in items.items],
                    'meta': {
                        'page': page,
                        'per_page': int(limit),
                        'total': items.total,
                        'pages': items.pages
                    }
                },
                message='Lista de animales obtenida exitosamente'
            )
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener animales: {str(e)}')
    
    @jwt_required()
    @animals_ns.expect(animal_model)
    def post(self):
        try:
            data = request.get_json()
            
            # Validar datos requeridos
            required_fields = ['sex', 'birth_date', 'weight', 'record', 'breeds_id']
            for field in required_fields:
                if field not in data or not data[field]:
                    return APIResponse.error(message=f'El campo {field} es requerido')
            
            # Crear nuevo animal
            animal = Animals(**data)
            db.session.add(animal)
            db.session.commit()
            
            return APIResponse.success(
                data=animal.to_namespace_dict(),
                message='Animal creado correctamente'
            )
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al crear animal: {str(e)}')

# @animals_ns.route('/<int:record_id>')
class AnimalDetail(Resource):
    @jwt_required()
    def get(self, record_id):
        try:
            animal = Animals.query.get_or_404(record_id)
            return APIResponse.success(data=animal.to_namespace_dict())
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener animal: {str(e)}')

    @jwt_required()
    @animals_ns.expect(animal_model)
    def put(self, record_id):
        try:
            animal = Animals.query.get_or_404(record_id)
            data = request.get_json()
            for key, value in data.items():
                setattr(animal, key, value)
            db.session.commit()
            return APIResponse.success(data=animal.to_namespace_dict(), message='Animal actualizado correctamente')
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al actualizar animal: {str(e)}')

    @jwt_required()
    def delete(self, record_id):
        try:
            animal = Animals.query.get_or_404(record_id)
            db.session.delete(animal)
            db.session.commit()
            return APIResponse.success(message='Animal eliminado correctamente')
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al eliminar animal: {str(e)}')

@animals_ns.route('/status')
class AnimalStatus(Resource):
    @jwt_required()
    def get(self):
        try:
            total = Animals.query.count()
            activos = Animals.query.filter(Animals.status == 'active').count()
            inactivos = total - activos
            return APIResponse.success(data={'total': total, 'activos': activos, 'inactivos': inactivos})
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener estadísticas: {str(e)}')