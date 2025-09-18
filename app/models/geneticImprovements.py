from app import db
from app.models.base_model import BaseModel, ValidationError

class GeneticImprovements(BaseModel):
    """Modelo para mejoras genéticas aplicadas a animales"""
    __tablename__ = 'genetic_improvements'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    details = db.Column(db.String(255), nullable=False)
    results = db.Column(db.String(255), nullable=False)
    genetic_event_technique = db.Column(db.String(255), nullable=False)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)

    # Relaciones
    animals = db.relationship('Animals', back_populates='genetic_improvements', lazy='selectin')

    # Campos y configuraciones para namespaces (antes estaban incompletos y producía items vacíos)
    _namespace_fields = [
        'id', 'date', 'details', 'results', 'genetic_event_technique', 'animal_id', 'created_at', 'updated_at'
    ]
    _namespace_relations = {
        'animals': {'fields': ['id', 'record', 'sex', 'status'], 'depth': 1}
    }
    _searchable_fields = ['details', 'results', 'genetic_event_technique']
    _filterable_fields = ['date', 'animal_id']
    _sortable_fields = ['id', 'date', 'created_at']
    _required_fields = ['date', 'details', 'results', 'genetic_event_technique', 'animal_id']

    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'details' in data and not data['details']:
            errors.append("El detalle no puede estar vacío")
        if 'results' in data and not data['results']:
            errors.append("El resultado no puede estar vacío")
        super()._validate_namespace_data(data)
        if errors:
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<GeneticImprovement {self.id}: {self.genetic_event_technique}>'
