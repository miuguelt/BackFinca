from flask import Blueprint, request, jsonify
from app import db
from app.models.treatments import Treatments
from app.utils.response import success_response, error_response

treatments_bp = Blueprint('treatments', __name__, url_prefix='/api/treatments')

@treatments_bp.route('/', methods=['GET'])
def get_treatments():
    """Obtiene lista de tratamientos con filtros y paginación"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        filters = request.args.to_dict()
        
        query = Treatments.query
        
        # Aplicar filtros
        if 'animal_id' in filters:
            query = query.filter_by(animal_id=filters['animal_id'])
        if 'treatment_date' in filters:
            query = query.filter_by(treatment_date=filters['treatment_date'])
        
        treatments = query.order_by(Treatments.treatment_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        data = {
            'treatments': [treatment.to_namespace_dict(depth=1) for treatment in treatments.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': treatments.total,
                'pages': treatments.pages
            }
        }
        
        return success_response(data, 'Tratamientos obtenidos exitosamente')
    
    except Exception as e:
        return error_response(f'Error al obtener tratamientos: {str(e)}', 500)

@treatments_bp.route('/<int:treatment_id>', methods=['GET'])
def get_treatment(treatment_id):
    """Obtiene un tratamiento específico"""
    try:
        treatment = Treatments.query.get_or_404(treatment_id)
        return success_response(treatment.to_namespace_dict(depth=1), 'Tratamiento obtenido exitosamente')
    
    except Exception as e:
        return error_response(f'Error al obtener tratamiento: {str(e)}', 500)

@treatments_bp.route('/', methods=['POST'])
def create_treatment():
    """Crea un nuevo tratamiento"""
    try:
        data = request.get_json()
        
        # Validación básica
        required_fields = ['treatment_date', 'description', 'frequency', 'dosis', 'animal_id']
        for field in required_fields:
            if field not in data:
                return error_response(f'Campo requerido faltante: {field}', 400)
        
        treatment = Treatments(**data)
        db.session.add(treatment)
        db.session.commit()
        
        return success_response(
            treatment.to_namespace_dict(depth=1), 
            'Tratamiento creado exitosamente',
            201
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error al crear tratamiento: {str(e)}', 500)

@treatments_bp.route('/<int:treatment_id>', methods=['PUT'])
def update_treatment(treatment_id):
    """Actualiza un tratamiento existente"""
    try:
        treatment = Treatments.query.get_or_404(treatment_id)
        data = request.get_json()
        
        for key, value in data.items():
            if hasattr(treatment, key):
                setattr(treatment, key, value)
        
        db.session.commit()
        
        return success_response(
            treatment.to_namespace_dict(depth=1), 
            'Tratamiento actualizado exitosamente'
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error al actualizar tratamiento: {str(e)}', 500)

@treatments_bp.route('/<int:treatment_id>', methods=['DELETE'])
def delete_treatment(treatment_id):
    """Elimina un tratamiento"""
    try:
        treatment = Treatments.query.get_or_404(treatment_id)
        db.session.delete(treatment)
        db.session.commit()
        
        return success_response({}, 'Tratamiento eliminado exitosamente')
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error al eliminar tratamiento: {str(e)}', 500)