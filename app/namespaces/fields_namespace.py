# app/namespaces/fields_namespace.py

from app.models.fields import Fields
from app.utils.namespace_helpers import create_optimized_namespace

# Create the optimized namespace for the Fields model
fields_ns = create_optimized_namespace(
    name='fields',
    description='🏞️ Gestión de Campos y Potreros',
    model_class=Fields,
    path='/fields'
)

from flask_restx import Resource
from app.models.animalFields import AnimalFields
from app.models.animals import Animals
from app.utils.response_handler import APIResponse, ResponseFormatter

@fields_ns.route('/<int:id>/animals')
class FieldAnimals(Resource):
    @fields_ns.doc('get_field_animals', description='Obtener animales asignados a un potrero')
    def get(self, id):
        """Obtiene la lista de animales actualmente asignados al campo"""
        # Verificar que el campo existe
        field = Fields.query.get(id)
        if not field:
            return APIResponse.not_found("Potrero")
            
        # Consultar asignaciones activas (removal_date is NULL)
        assignments = AnimalFields.query.filter_by(
            field_id=id,
            removal_date=None
        ).all()
        
        # Obtener los IDs de los animales
        animal_ids = [a.animal_id for a in assignments]
        
        if not animal_ids:
             return APIResponse.success(data=[], message=f"No hay animales en el potrero {field.name}")
             
        # Consultar los animales con sus detalles
        query = Animals.query.filter(Animals.id.in_(animal_ids))
        
        # Aplicar ordenamiento por defecto
        query = query.order_by(Animals.record.asc())
        
        animals = query.all()
        
        # Serializar usando la lógica de namespaces para incluir campos calculados
        # Usamos to_namespace_dict con depth=1 para incluir relaciones básicas si es necesario
        data = [a.to_namespace_dict(include_relations=True, depth=1) for a in animals]
        
        # Sanitizar para frontend
        data = ResponseFormatter.sanitize_for_frontend(data)
        
        return APIResponse.success(
            data=data, 
            message=f"Animales en el potrero {field.name} obtenidos exitosamente",
            meta={"count": len(data)}
        )
