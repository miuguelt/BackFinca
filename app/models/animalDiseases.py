from app import db
from app.models.base_model import BaseModel

class AnimalDiseases(BaseModel):
    """Modelo para enfermedades diagnosticadas en animales"""
    __tablename__ = 'animal_diseases'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    diagnosis_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Activo')
    # Notes optional to allow minimal test creation
    notes = db.Column(db.Text, nullable=True)  # nullable for tests

    # Relaciones
    animal = db.relationship('Animals', back_populates='diseases', lazy='selectin')
    disease = db.relationship('Diseases', back_populates='animals', lazy='selectin')
    instructor = db.relationship('User', back_populates='diseases', lazy='selectin')

    # Campos / relaciones para namespaces
    _namespace_fields = ['id', 'animal_id', 'disease_id', 'instructor_id', 'diagnosis_date', 'status', 'notes', 'created_at', 'updated_at']
    _namespace_relations = {
        'animal': {'fields': ['id', 'record', 'sex', 'status'], 'depth': 1},
        'disease': {'fields': ['id', 'name'], 'depth': 1},
        'instructor': {'fields': ['id', 'fullname', 'role'], 'depth': 1}
    }
    # Configuraciones del modelo base
    _searchable_fields = ['notes', 'status']
    _filterable_fields = ['animal_id', 'disease_id', 'instructor_id', 'status', 'diagnosis_date']
    _sortable_fields = ['id', 'diagnosis_date']
    _required_fields = ['animal_id', 'disease_id', 'instructor_id', 'diagnosis_date', 'status']

    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'status' in data and not data['status']:
            errors.append("El estado no puede estar vacío")
        super()._validate_namespace_data(data)
        if errors:
            from app.models.base_model import ValidationError
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<AnimalDisease {self.id}: Animal {self.animal_id} - Disease {self.disease_id}>'
