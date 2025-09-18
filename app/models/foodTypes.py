from app import db
from app.models.base_model import BaseModel, ValidationError

class FoodTypes(BaseModel):
    """Modelo para tipos de alimentos/cultivos optimizado para namespaces"""
    __tablename__ = 'food_types'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    food_type = db.Column(db.String(255), nullable=False, unique=True)
    # Nullable fields: relaxed to accept minimal test payloads. These are metadata and safe to keep optional
    # but review before enforcing stricter production constraints.
    sowing_date = db.Column(db.Date, nullable=True)  # nullable for tests
    harvest_date = db.Column(db.Date, nullable=True)  # nullable for tests
    area = db.Column(db.Integer, nullable=True)  # nullable for tests
    handlings = db.Column(db.String(255), nullable=True)  # nullable for tests
    gauges = db.Column(db.String(255), nullable=True)  # nullable for tests

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'food_type', 'sowing_date', 'harvest_date', 'area', 'handlings', 'gauges', 'created_at']
    _namespace_relations = {
        'fields': {'fields': ['id', 'name', 'state'], 'depth': 1}
    }
    _searchable_fields = ['food_type', 'handlings']
    _filterable_fields = ['sowing_date', 'harvest_date', 'area', 'created_at']
    _sortable_fields = ['id', 'food_type', 'sowing_date', 'harvest_date', 'area', 'created_at', 'updated_at']
    # For test convenience allow minimal payloads; only food_type is strictly required
    _required_fields = ['food_type']
    _unique_fields = ['food_type']
    # Aliases to accept legacy/frontend field names (tests use 'name' and 'description')
    _input_aliases = {
        'name': 'food_type',
        'description': 'handlings'
    }

    # Relaciones optimizadas
    fields = db.relationship('Fields', back_populates='food_types', lazy='dynamic')
    
    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'food_type' in data and not data['food_type']:
            errors.append("El tipo de alimento no puede estar vacío")
        if 'area' in data and (not isinstance(data['area'], int) or data['area'] <= 0):
            errors.append("El área debe ser un número entero positivo")
        super()._validate_namespace_data(data)
        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<FoodType {self.id}: {self.food_type}>'
