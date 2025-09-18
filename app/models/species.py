from app import db
from app.models.base_model import BaseModel, ValidationError

class Species(BaseModel):
    """Modelo para especies de animales optimizado para namespaces"""
    __tablename__ = 'species'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    
    # Configuración específica para namespaces
    _namespace_fields = ['id', 'name', 'created_at']
    _namespace_relations = {
        'breeds': {'fields': ['id', 'name'], 'depth': 1}
    }
    _searchable_fields = ['name']
    _filterable_fields = ['created_at']
    _sortable_fields = ['id', 'name', 'created_at', 'updated_at']
    _required_fields = ['name']
    _unique_fields = ['name']

    # Relaciones optimizadas
    breeds = db.relationship('Breeds', back_populates='species', lazy='dynamic')

    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'name' in data and not data['name']:
            errors.append("El nombre de la especie no puede estar vacío")
        super()._validate_namespace_data(data)
        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<Species {self.id}: {self.name}>'
