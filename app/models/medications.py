from app import db
from app.models.base_model import BaseModel, ValidationError

class Medications(BaseModel):
    """Modelo para medicamentos utilizados en tratamientos optimizado para namespaces"""
    __tablename__ = 'medications'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=False)
    # Optional metadata fields; nullable to support minimal test fixtures
    indications = db.Column(db.String(255), nullable=True)  # nullable for tests
    dosis = db.Column(db.String(50), nullable=True)  # nullable for tests
    contraindications = db.Column(db.String(255), nullable=True)  # Opcional, nullable for tests
    route_administration_id = db.Column(db.Integer, db.ForeignKey('route_administrations.id'), nullable=False)
    availability = db.Column(db.Boolean, nullable=False, default=True)

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'name', 'description', 'dosis', 'indications', 'contraindications', 'route_administration_id', 'availability', 'created_at']
    _namespace_relations = {
        'treatments': {'fields': ['id', 'treatment_id'], 'depth': 1},
        'route_administration_rel': {'fields': ['id', 'name'], 'depth': 1}
    }
    _searchable_fields = ['name', 'description', 'indications']
    _filterable_fields = ['route_administration_id', 'availability', 'created_at']
    _sortable_fields = ['id', 'name', 'created_at', 'updated_at']
    _required_fields = ['name', 'description', 'route_administration_id']
    _unique_fields = ['name']

    # Relaciones optimizadas
    treatments = db.relationship('TreatmentMedications', back_populates='medications', lazy='dynamic')
    # OPTIMIZED: Changed from lazy='select' to lazy='selectin' to prevent N+1 queries
    route_administration_rel = db.relationship('RouteAdministration', back_populates='medications', lazy='selectin')
    
    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'name' in data and not data['name']:
            errors.append("El nombre del medicamento no puede estar vacío")
        if 'description' in data and not data['description']:
            errors.append("La descripción no puede estar vacía")
        # route_administration_id may be provided directly or the legacy 'route_administration' string may be used.
        if 'route_administration_id' in data and not data['route_administration_id']:
            errors.append("La ruta de administración es requerida")
        super()._validate_namespace_data(data)
        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<Medication {self.id}: {self.name}>'
