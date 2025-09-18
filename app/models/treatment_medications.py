from app import db
from app.models.base_model import BaseModel

class TreatmentMedications(BaseModel):
    """Modelo de relación entre tratamientos y medicamentos"""
    __tablename__ = 'treatment_medications'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatments.id'), nullable=False)
    medication_id = db.Column(db.Integer, db.ForeignKey('medications.id'), nullable=False)

    # Relaciones
    treatments = db.relationship('Treatments', back_populates='medication_treatments', lazy='selectin')
    medications = db.relationship('Medications', back_populates='treatments', lazy='selectin')

    # Campos / relaciones para namespaces
    _namespace_fields = ['id', 'treatment_id', 'medication_id', 'created_at', 'updated_at']
    _namespace_relations = {
        'treatments': {'fields': ['id', 'treatment_date', 'animal_id'], 'depth': 1},
        'medications': {'fields': ['id', 'name', 'dosis'], 'depth': 1}
    }
    # Configuraciones del modelo base
    _filterable_fields = ['treatment_id', 'medication_id']
    _sortable_fields = ['id']
    _required_fields = ['treatment_id', 'medication_id']

    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'treatment_id' in data and not data['treatment_id']:
            errors.append("El tratamiento es obligatorio")
        if 'medication_id' in data and not data['medication_id']:
            errors.append("El medicamento es obligatorio")
        super()._validate_namespace_data(data)
        if errors:
            from app.models.base_model import ValidationError
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<TreatmentMedication {self.id}: Treatment {self.treatment_id} - Medication {self.medication_id}>'
