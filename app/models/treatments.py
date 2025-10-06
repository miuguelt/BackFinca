from app import db
from app.models.base_model import BaseModel

class Treatments(BaseModel):
    """Modelo para tratamientos aplicados a animales optimizado para namespaces"""
    __tablename__ = 'treatments'
    # Índices de rendimiento para historial y consultas recientes
    __table_args__ = (
        db.Index('ix_treatments_animal_date', 'animal_id', 'treatment_date'),
        db.Index('ix_treatments_created_at', 'created_at'),
    )
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    treatment_date = db.Column(db.Date, nullable=False)  # Simplificado a una sola fecha
    description = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.String(255), nullable=False)
    observations = db.Column(db.String(255), nullable=True)  # Opcional
    dosis = db.Column(db.String(255), nullable=False)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    
    # Configuración específica para namespaces
    _namespace_fields = ['id', 'treatment_date', 'description', 'frequency', 'observations', 'dosis', 'animal_id', 'created_at', 'updated_at']
    _namespace_relations = {
        'animals': {'fields': ['id', 'record', 'sex', 'status'], 'depth': 1},
        'vaccines_treatments': {'fields': ['id', 'vaccine_id'], 'depth': 1},
        'medication_treatments': {'fields': ['id', 'medication_id'], 'depth': 1}
    }
    _searchable_fields = ['description', 'observations']
    _filterable_fields = ['animal_id', 'treatment_date', 'created_at']
    _sortable_fields = ['id', 'treatment_date', 'created_at', 'updated_at']
    _required_fields = ['treatment_date', 'description', 'frequency', 'dosis', 'animal_id']
    _unique_fields = []

    # Relaciones optimizadas
    animals = db.relationship('Animals', back_populates='treatments', lazy='selectin')
    vaccines_treatments = db.relationship('TreatmentVaccines', back_populates='treatments', lazy='dynamic')
    medication_treatments = db.relationship('TreatmentMedications', back_populates='treatments', lazy='dynamic')
    
    def to_namespace_dict(self, include_relations: bool = False, depth: int = 1, fields=None):
        """Serializa el modelo a diccionario para namespace manteniendo compatibilidad con BaseModel"""
        return super().to_namespace_dict(include_relations=include_relations, depth=depth, fields=fields)
    
    @classmethod
    def _validate_namespace_data(cls, data):
        errors = []
        if 'description' in data and not data['description']:
            errors.append("La descripción no puede estar vacía")
        if 'dosis' in data and not data['dosis']:
            errors.append("La dosis no puede estar vacía")
        super()._validate_namespace_data(data)
        if errors:
            from app.models.base_model import ValidationError
            raise ValidationError('; '.join(errors), code="validation_error")

    def __repr__(self):
        return f'<Treatment {self.id}: {self.description[:30]}...>'
