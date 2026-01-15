from app import db
from app.models.base_model import BaseModel

class AnimalFields(BaseModel):
    """Modelo para asignaciones de animales a campos/potreros"""
    __tablename__ = 'animal_fields'
    __table_args__ = (
        db.UniqueConstraint('animal_id', 'field_id', 'assignment_date', name='uq_animal_fields_animal_field_date'),
    )
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
    assignment_date = db.Column(db.Date, nullable=False)
    # Nullable to allow creating assignments without removal_date/notes in tests
    removal_date = db.Column(db.Date, nullable=True)  # nullable for tests
    notes = db.Column(db.Text, nullable=True)  # nullable for tests

    # Relaciones
    animal = db.relationship('Animals', back_populates='animal_fields', lazy='selectin')
    field = db.relationship('Fields', back_populates='animal_fields', lazy='selectin')

    # Campos / relaciones para namespaces
    _namespace_fields = ['id', 'animal_id', 'field_id', 'assignment_date', 'removal_date', 'notes', 'created_at', 'updated_at']
    _namespace_relations = {
        'animal': {'fields': ['id', 'record', 'sex', 'status'], 'depth': 1},
        'field': {'fields': ['id', 'name', 'ubication', 'capacity'], 'depth': 1}
    }
    # Configuraciones del modelo base
    _searchable_fields = ['notes']
    _filterable_fields = ['animal_id', 'field_id', 'assignment_date', 'removal_date']
    _sortable_fields = ['id', 'assignment_date', 'removal_date']
    _required_fields = ['animal_id', 'field_id', 'assignment_date']

    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'assignment_date' in data and not data['assignment_date']:
            errors.append("La fecha de asignación no puede estar vacía")
        super()._validate_namespace_data(data)
        if errors:
            from app.models.base_model import ValidationError
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<AnimalField {self.id}: Animal {self.animal_id} - Field {self.field_id}>'
