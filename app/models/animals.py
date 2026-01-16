from app import db 
import enum
from datetime import date
from app.models.base_model import BaseModel, ValidationError

class Sex(enum.Enum):
    """Enumeración para el sexo de los animales"""
    Hembra = 'Hembra'
    Macho = 'Macho'
    
    @classmethod
    def get_choices(cls):
        return [(choice.value, choice.value) for choice in cls]
        
    def __str__(self):
        """Devuelve el valor como string para facilitar la conversión"""
        return str(self.value)
        
    def __repr__(self):
        """Representación detallada para debug"""
        return f"{self.__class__.__name__}.{self.name}"

class AnimalStatus(enum.Enum):
    """Enumeración para el estado de los animales"""
    Vivo = 'Vivo'
    Vendido = 'Vendido'
    Muerto = 'Muerto'
    
    @classmethod
    def get_choices(cls):
        return [(choice.value, choice.value) for choice in cls]
        
    def __str__(self):
        """Devuelve el valor como string para facilitar la conversión"""
        return str(self.value)
        
    def __repr__(self):
        """Representación detallada para debug"""
        return f"{self.__class__.__name__}.{self.name}"
    
class Animals(BaseModel):
    """Modelo para animales optimizado para namespaces"""
    __tablename__ = 'animals'
    # Índices de rendimiento: búsquedas frecuentes por (breeds_id,status) y ordenaciones/filtrado recientes
    __table_args__ = (
        db.Index('ix_animals_breeds_status', 'breeds_id', 'status'),
        db.Index('ix_animals_created_at', 'created_at'),
        db.Index('ix_animals_updated_at', 'updated_at'),  # Para ?since= y /metadata
    )
    
    id = db.Column(db.Integer, primary_key=True)
    sex = db.Column(db.Enum(Sex), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    record = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.Enum(AnimalStatus), default=AnimalStatus.Vivo)

    breeds_id = db.Column(db.Integer, db.ForeignKey('breeds.id'), nullable=False) 
    idFather = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=True)
    idMother = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=True)
    
    # Configuración específica para namespaces
    _namespace_fields = ['id', 'record', 'sex', 'birth_date', 'weight', 'status', 'breeds_id', 'idFather', 'idMother', 'created_at', 'updated_at']
    _namespace_relations = {
        'breed': {'fields': ['id', 'name', 'species_id'], 'depth': 1},
        'father': {'fields': ['id', 'record', 'sex'], 'depth': 1},
        'mother': {'fields': ['id', 'record', 'sex'], 'depth': 1},
        'treatments': {'fields': ['id', 'treatment_date', 'medication_id'], 'depth': 1},
        'vaccinations': {'fields': ['id', 'vaccination_date', 'vaccine_id'], 'depth': 1},
        'diseases': {'fields': ['id', 'disease_id', 'diagnosis_date'], 'depth': 1},
        'controls': {'fields': ['id', 'checkup_date', 'weight', 'height'], 'depth': 1},
        'images': {'fields': ['id', 'filename', 'filepath', 'is_primary'], 'depth': 1}
    }
    _searchable_fields = ['record']
    _filterable_fields = ['sex', 'status', 'breeds_id', 'birth_date', 'weight', 'created_at', 'idFather', 'idMother']
    _sortable_fields = ['id', 'record', 'birth_date', 'weight', 'created_at', 'updated_at']
    _required_fields = ['sex', 'birth_date', 'weight', 'record', 'breeds_id']
    _unique_fields = ['record']
    _enum_fields = {'sex': Sex, 'status': AnimalStatus}
    # Compatibilidad con claves usadas por frontend / legacy
    _input_aliases = {'father_id': 'idFather', 'mother_id': 'idMother'}

    # Relaciones optimizadas
    breed = db.relationship('Breeds', back_populates='animals', lazy='selectin')
    # OPTIMIZED: Changed from lazy='select' to lazy='joined' to prevent N+1 queries in genealogy
    father = db.relationship('Animals', remote_side=[id], foreign_keys=[idFather], lazy='joined')
    mother = db.relationship('Animals', remote_side=[id], foreign_keys=[idMother], lazy='joined')

    # Relaciones con lazy loading optimizado y cascade delete
    treatments = db.relationship('Treatments', back_populates='animals', lazy='dynamic', cascade='all, delete-orphan')
    vaccinations = db.relationship('Vaccinations', back_populates='animals', lazy='dynamic', cascade='all, delete-orphan')
    diseases = db.relationship('AnimalDiseases', back_populates='animal', lazy='dynamic', cascade='all, delete-orphan')
    controls = db.relationship('Control', back_populates='animals', lazy='dynamic',
                              order_by='desc(Control.checkup_date)', cascade='all, delete-orphan')
    genetic_improvements = db.relationship('GeneticImprovements', back_populates='animals', lazy='dynamic', cascade='all, delete-orphan')
    animal_fields = db.relationship('AnimalFields', back_populates='animal', lazy='dynamic', cascade='all, delete-orphan')
    images = db.relationship('AnimalImages', back_populates='animal', lazy='dynamic', cascade='all, delete-orphan')

    @classmethod
    def _validate_and_normalize(cls, data, is_update=False, instance_id=None):
        """
        Sobrescribe para añadir validaciones y normalizaciones específicas de Animales.
        """
        # Compatibilidad: permitir aliases del frontend (father_id/mother_id)
        if isinstance(data, dict):
            if 'father_id' in data and 'idFather' not in data:
                data['idFather'] = data.pop('father_id')
            if 'mother_id' in data and 'idMother' not in data:
                data['idMother'] = data.pop('mother_id')

        # Normalizar y validar fecha de nacimiento
        if 'birth_date' in data and data['birth_date']:
            if isinstance(data['birth_date'], str):
                try:
                    data['birth_date'] = date.fromisoformat(data['birth_date'])
                except (ValueError, TypeError):
                    raise ValidationError("La fecha de nacimiento debe tener formato YYYY-MM-DD")
            
            if data['birth_date'] > date.today():
                raise ValidationError("La fecha de nacimiento no puede ser futura")

        # Validar peso
        if 'weight' in data and data.get('weight') is not None:
            if not isinstance(data['weight'], int) or data['weight'] <= 0:
                raise ValidationError("El peso debe ser un número entero positivo")

        # Validar genealogía
        if data.get('idFather') and data.get('idMother') and data['idFather'] == data['idMother']:
            raise ValidationError("El padre y la madre no pueden ser el mismo animal")

        # Llamar a la validación base para requeridos, únicos y enums
        return super()._validate_and_normalize(data, is_update, instance_id)

    @property
    def age_in_days(self):
        """Calcula la edad del animal en días."""
        if not self.birth_date:
            return None
        return (date.today() - self.birth_date).days

    @property
    def age_in_months(self):
        """Calcula la edad aproximada del animal en meses."""
        days = self.age_in_days
        return round(days / 30.44) if days is not None else None

    def is_adult(self, adult_age_months=12):
        """Determina si el animal es adulto basado en una edad en meses."""
        months = self.age_in_months
        return months is not None and months >= adult_age_months

    def to_namespace_dict(self, include_relations=False, depth=1, fields=None):
        """
        Añade campos calculados a la serialización del modelo.
        """
        data = super().to_namespace_dict(include_relations, depth, fields)
        data.update({
            'age_in_days': self.age_in_days,
            'age_in_months': self.age_in_months,
            'is_adult': self.is_adult()
        })
        return data

    def __repr__(self):
        return f'<Animal {self.id}: {self.record}>'

