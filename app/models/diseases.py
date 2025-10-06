from app import db
from app.models.base_model import BaseModel, ValidationError

class Diseases(BaseModel):
    """Modelo para enfermedades que pueden afectar a los animales optimizado para namespaces"""
    __tablename__ = 'diseases'
    __table_args__ = (
        db.Index('ix_diseases_updated_at', 'updated_at'),
        db.Index('ix_diseases_created_at', 'created_at'),
    )

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    symptoms = db.Column(db.String(255), nullable=False)
    details = db.Column(db.String(255), nullable=False)

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'name', 'symptoms', 'details', 'created_at']
    _namespace_relations = {
        'animals': {'fields': ['id', 'animal_id', 'diagnosis_date'], 'depth': 1},
        'vaccines': {'fields': ['id', 'name', 'type'], 'depth': 1}
    }
    _searchable_fields = ['name', 'symptoms', 'details']
    _filterable_fields = ['created_at']
    _sortable_fields = ['id', 'name', 'created_at', 'updated_at']
    _required_fields = ['name', 'symptoms', 'details']
    _unique_fields = ['name']

    # Configuración de caché: datos maestros, cambian poco, caché público largo
    _cache_config = {
        'ttl': 1800,  # 30 minutos
        'type': 'public',
        'strategy': 'cache-first',
        'max_age': 1800,
        'stale_while_revalidate': 600,  # 10 minutos
    }

    # Relaciones optimizadas
    animals = db.relationship('AnimalDiseases', back_populates='disease', lazy='dynamic')
    vaccines = db.relationship('Vaccines', back_populates='diseases', lazy='dynamic')

    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        for field in ['name', 'symptoms', 'details']:
            if field in data:
                if not data[field] or not str(data[field]).strip():
                    errors.append(f"El campo '{field}' no puede estar vacío")
                elif len(str(data[field]).strip()) < 3:
                    errors.append(f"El campo '{field}' debe tener al menos 3 caracteres")
        super()._validate_namespace_data(data)
        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<Disease {self.id}: {self.name}>'
