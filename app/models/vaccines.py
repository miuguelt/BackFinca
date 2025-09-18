from app import db
import enum
from app.models.base_model import BaseModel

class VaccineType(enum.Enum):
    """Tipos de vacunas disponibles"""
    Atenuada = "Atenuada"
    Inactivada = "Inactivada"
    Toxoide = "Toxoide"
    Subunidad = "Subunidad"
    Conjugada = "Conjugada"
    Recombinante = "Recombinante"
    Adn = "Adn"
    Arn = "Arn"
    
    @classmethod
    def get_choices(cls):
        return [(choice.value, choice.value) for choice in cls]
        
    def __str__(self):
        """Devuelve el valor como string para facilitar la conversión"""
        return str(self.value)
        
    def __repr__(self):
        """Representación detallada para debug"""
        return f"{self.__class__.__name__}.{self.name}"

class Vaccines(BaseModel):
    """Modelo para vacunas utilizadas en el sistema optimizado para namespaces"""
    __tablename__ = 'vaccines'
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    dosis = db.Column(db.String(255), nullable=False)
    route_administration_id = db.Column(db.Integer, db.ForeignKey('route_administrations.id'), nullable=False)
    vaccination_interval = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Enum(VaccineType), nullable=False)  # Simplificado
    national_plan = db.Column(db.String(255), nullable=False)
    target_disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)
    
    # Configuración específica para namespaces
    _namespace_fields = ['id', 'name', 'dosis', 'route_administration_id', 'vaccination_interval', 'type', 'national_plan', 'target_disease_id', 'created_at']
    # Reducir carga automática de relaciones pesadas para listados por defecto
    _namespace_relations = {}
    _searchable_fields = ['name', 'national_plan']
    _filterable_fields = ['target_disease_id', 'type', 'route_administration_id', 'created_at']
    _sortable_fields = ['id', 'name', 'created_at', 'updated_at']
    _required_fields = ['name', 'dosis', 'route_administration_id', 'vaccination_interval', 'type', 'national_plan', 'target_disease_id']
    _unique_fields = ['name']
    _enum_fields = {'type': VaccineType}
    
    # Relaciones optimizadas
    diseases = db.relationship('Diseases', back_populates='vaccines', lazy='selectin')
    treatments = db.relationship('TreatmentVaccines', back_populates='vaccines', lazy='dynamic')
    vaccinations = db.relationship('Vaccinations', back_populates='vaccines', lazy='dynamic')
    route_administration_rel = db.relationship('RouteAdministration', back_populates='vaccines', lazy='select')

    def __repr__(self):
        return f'<Vaccine {self.id}: {self.name}>'
