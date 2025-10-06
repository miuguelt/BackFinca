from app import db 
import enum
from datetime import date, timedelta
from app.models.base_model import BaseModel, ValidationError

class HealthStatus(enum.Enum):
    """Estados de salud para controles veterinarios"""
    Excelente = "Excelente"
    Bueno = "Bueno"
    Regular = "Regular"
    Malo = "Malo"
    Sano = "Sano"
    
    @classmethod
    def get_choices(cls):
        return [(choice.value, choice.value) for choice in cls]
        
    def __str__(self):
        """Devuelve el valor como string para facilitar la conversión"""
        return str(self.value)
        
    def __repr__(self):
        """Representación detallada para debug"""
        return f"{self.__class__.__name__}.{self.name}"

class Control(BaseModel):
    """Modelo para controles de salud de animales optimizado para namespaces"""
    __tablename__ = 'control'
    # Índices para acelerar historiales por animal y consultas recientes
    __table_args__ = (
        db.Index('ix_control_animal_checkup', 'animal_id', 'checkup_date'),
        db.Index('ix_control_created_at', 'created_at'),
    )
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    checkup_date = db.Column(db.Date, nullable=False)
    health_status = db.Column(db.Enum(HealthStatus), nullable=False)
    # Physical measurement fields and description are optional; kept nullable for test flexibility
    weight = db.Column(db.Integer, nullable=True)  # nullable for tests
    height = db.Column(db.Integer, nullable=True)  # nullable for tests
    description = db.Column(db.String(255), nullable=True)  # nullable for tests
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'checkup_date', 'health_status', 'weight', 'height', 'description', 'animal_id', 'created_at', 'updated_at']
    _namespace_relations = {
        'animals': {'fields': ['id', 'record', 'sex', 'status'], 'depth': 1}
    }
    _searchable_fields = ['description']
    _filterable_fields = ['animal_id', 'health_status', 'checkup_date', 'created_at']
    _sortable_fields = ['id', 'checkup_date', 'created_at', 'updated_at']
    _required_fields = ['checkup_date', 'health_status', 'animal_id']
    _unique_fields = []
    _enum_fields = {'health_status': HealthStatus}

    # Relación optimizada
    animals = db.relationship('Animals', back_populates='controls', lazy='select')

    @classmethod
    def _validate_and_normalize(cls, data, is_update=False, instance_id=None):
        """
        Sobrescribe para añadir validaciones y normalizaciones específicas de Control.
        """
        # Validar y normalizar fecha de control
        if 'checkup_date' in data and data['checkup_date']:
            if isinstance(data['checkup_date'], str):
                try:
                    data['checkup_date'] = date.fromisoformat(data['checkup_date'])
                except (ValueError, TypeError):
                    raise ValidationError("La fecha de control debe tener formato YYYY-MM-DD")
            
            if data['checkup_date'] > date.today():
                raise ValidationError("La fecha de control no puede ser futura")

        # Validar medidas físicas
        for field in ['weight', 'height']:
            if field in data and data.get(field) is not None:
                if not isinstance(data[field], int) or data[field] <= 0:
                    raise ValidationError(f"El campo '{field}' debe ser un número entero positivo")

        # Validar animal_id
        if 'animal_id' in data and data.get('animal_id') is not None:
            if not isinstance(data['animal_id'], int) or data['animal_id'] <= 0:
                raise ValidationError("El 'animal_id' debe ser un número entero positivo")

        # Llamar a la validación base
        return super()._validate_and_normalize(data, is_update, instance_id)

    def __repr__(self):
        return f'<Control {self.id}: {self.health_status.value if self.health_status else "N/A"} on {self.checkup_date}>'
