from app import db
from app.models.base_model import BaseModel, ValidationError

class RouteAdministration(BaseModel):
    """Modelo para rutas de administración de medicamentos"""
    __tablename__ = 'route_administrations'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Boolean, nullable=False, default=True)

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'name', 'description', 'status', 'created_at', 'updated_at']
    # Reducimos las relaciones por defecto para evitar cargas innecesarias en listados
    _namespace_relations = {}
    _searchable_fields = ['name', 'description']
    _filterable_fields = ['status', 'created_at']
    _sortable_fields = ['id', 'name', 'created_at', 'updated_at']
    _required_fields = ['name']
    _unique_fields = ['name']

    # Relaciones
    medications = db.relationship('Medications', back_populates='route_administration_rel', lazy='dynamic')
    vaccines = db.relationship('Vaccines', back_populates='route_administration_rel', lazy='dynamic')
    
    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'name' in data and not data['name']:
            errors.append("El nombre de la ruta de administración no puede estar vacío")
        if 'name' in data and len(data['name']) > 50:
            errors.append("El nombre no puede exceder 50 caracteres")
        super()._validate_namespace_data(data)
        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<RouteAdministration {self.id}: {self.name}>'
