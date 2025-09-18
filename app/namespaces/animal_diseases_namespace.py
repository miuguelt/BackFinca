from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_current_user
from flask_restx import Resource, Namespace, fields
from app import db, models
from app.utils.response_handler import APIResponse
from app.utils.namespace_helpers import create_optimized_namespace

model_for_update = models.AnimalDisease.__table__.columns.keys()

animal_diseases_ns = create_optimized_namespace('animal-diseases', description='Gestión de enfermedades de animales', model_class=models.AnimalDisease)

class AnimalDiseaseById(Resource):
    @jwt_required()
    def get(self, record_id):
        try:
            disease_record = db.session.query(models.AnimalDisease).filter_by(id=record_id).first()
            if not disease_record:
                return APIResponse.error(message='Registro de enfermedad no encontrado', status_code=404)
            return APIResponse.success(data=disease_record.to_dict())
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al obtener la enfermedad: {str(e)}', status_code=500)
    
    @jwt_required()
    def put(self, record_id):
        try:
            data = request.get_json()
            disease_record = db.session.query(models.AnimalDisease).filter_by(id=record_id).first()
            if not disease_record:
                return APIResponse.error(message='Registro de enfermedad no encontrado', status_code=404)
            
            for attr, value in data.items():
                if attr in model_for_update:
                    setattr(disease_record, attr, value)
            
            db.session.commit()
            return APIResponse.success(message='Enfermedad actualizada exitosamente', data=disease_record.to_dict())
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al actualizar la enfermedad: {str(e)}', status_code=500)
    
    @jwt_required()
    def delete(self, record_id):
        try:
            disease_record = db.session.query(models.AnimalDisease).filter_by(id=record_id).first()
            if not disease_record:
                return APIResponse.error(message='Registro de enfermedad no encontrado', status_code=404)
            
            db.session.delete(disease_record)
            db.session.commit()
            return APIResponse.success(message='Enfermedad eliminada exitosamente')
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al eliminar la enfermedad: {str(e)}', status_code=500)
    
    @jwt_required()
    def patch(self, record_id):
        try:
            data = request.get_json()
            disease_record = db.session.query(models.AnimalDisease).filter_by(id=record_id).first()
            if not disease_record:
                return APIResponse.error(message='Registro de enfermedad no encontrado', status_code=404)
            
            for attr, value in data.items():
                if attr in model_for_update:
                    setattr(disease_record, attr, value)
            
            db.session.commit()
            return APIResponse.success(message='Enfermedad actualizada parcialmente', data=disease_record.to_dict())
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al actualizar parcialmente la enfermedad: {str(e)}', status_code=500)

class AnimalDiseasesList(Resource):
    @jwt_required()
    def get(self):
        try:
            page = request.args.get('page', default=1, type=int) or 1
            limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
            search = request.args.get('search', '')
            
            query = db.session.query(models.AnimalDisease)
            if search:
                query = query.filter(
                    models.AnimalDisease.disease_name.ilike(f'%{search}%')
                )
            
            diseases = query.paginate(page=page, per_page=int(limit), error_out=False)
            return APIResponse.success(
                data={
                    'items': [d.to_dict() for d in diseases.items],
                    'total': diseases.total,
                    'pages': diseases.pages,
                    'page': page
                }
            )
        except Exception as e:
            return APIResponse.error(message=f'Error al obtener lista de enfermedades: {str(e)}', status_code=500)
    
    @jwt_required()
    def post(self):
        try:
            data = request.get_json()
            
            # Validar existencia de animal y enfermedad
            animal = db.session.query(models.Animal).filter_by(id=data.get('animal_id')).first()
            if not animal:
                return APIResponse.error(message='Animal no encontrado', status_code=404)
            
            disease = db.session.query(models.Disease).filter_by(id=data.get('disease_id')).first()
            if not disease:
                return APIResponse.error(message='Enfermedad no encontrada', status_code=404)
            
            # Verificar duplicado
            existing = db.session.query(models.AnimalDisease).filter_by(
                animal_id=data['animal_id'],
                disease_id=data['disease_id']
            ).first()
            if existing:
                return APIResponse.error(message='Registro de enfermedad ya existe para este animal', status_code=409)
            
            new_disease_record = models.AnimalDisease(**data)
            db.session.add(new_disease_record)
            db.session.commit()
            
            return APIResponse.success(
                message='Enfermedad registrada exitosamente',
                data=new_disease_record.to_dict()
            )
        except Exception as e:
            db.session.rollback()
            return APIResponse.error(message=f'Error al crear registro de enfermedad: {str(e)}', status_code=500)

# Agregar recursos al namespace (delegado a create_optimized_namespace)
# animal_diseases_ns.add_resource(AnimalDiseaseById, '/<int:record_id>')
# animal_diseases_ns.add_resource(AnimalDiseasesList, '/')
