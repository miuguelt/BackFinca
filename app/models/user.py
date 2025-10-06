from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base_model import BaseModel
import enum

class Role(enum.Enum):
    Aprendiz = 'Aprendiz'
    Instructor = 'Instructor'
    Administrador = 'Administrador'

    @classmethod
    def get_choices(cls):
        return [(c.value, c.value) for c in cls]
        
    def __str__(self):
        """Devuelve el valor como string para facilitar la conversión"""
        return str(self.value)
    
    def __repr__(self):
        """Representación detallada para debug"""
        return f"{self.__class__.__name__}.{self.name}"

class User(BaseModel):
    """Modelo de usuario optimizado para namespaces"""
    __tablename__ = 'user'
    __table_args__ = (
        db.Index('ix_user_updated_at', 'updated_at'),
        db.Index('ix_user_created_at', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identification = db.Column(db.BigInteger, unique=True, nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(40), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    role = db.Column(db.Enum(Role), nullable=False)
    status = db.Column(db.Boolean, default=True)

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'identification', 'fullname', 'email', 'phone', 'address', 'role', 'status', 'created_at', 'updated_at']
    _namespace_relations = {
        'diseases': {'fields': ['id', 'animal_id', 'disease_id', 'diagnosis_date'], 'depth': 1},
        'vaccines_as_apprentice': {'fields': ['id', 'animal_id', 'vaccine_id', 'vaccination_date'], 'depth': 1},
        'vaccines_as_instructor': {'fields': ['id', 'animal_id', 'vaccine_id', 'vaccination_date'], 'depth': 1}
    }
    _searchable_fields = ['fullname', 'email']
    _filterable_fields = ['role', 'status', 'created_at']
    _sortable_fields = ['id', 'fullname', 'email', 'identification', 'created_at', 'updated_at']
    _required_fields = ['identification', 'fullname', 'password', 'email', 'phone', 'role']
    _unique_fields = ['identification', 'email', 'phone']
    _enum_fields = {'role': Role}

    # Configuración de caché: datos de usuario son privados y cambian frecuentemente
    _cache_config = {
        'ttl': 60,  # 1 minuto
        'type': 'private',
        'strategy': 'network-first',
        'max_age': 60,
        'stale_while_revalidate': 30,
    }

    # Relaciones optimizadas
    diseases = db.relationship('AnimalDiseases', back_populates='instructor', lazy='dynamic')
    vaccines_as_apprentice = db.relationship('Vaccinations', foreign_keys='Vaccinations.apprentice_id', back_populates='apprentice', lazy='dynamic')
    vaccines_as_instructor = db.relationship('Vaccinations', foreign_keys='Vaccinations.instructor_id', back_populates='instructor', lazy='dynamic')

    def set_password(self, password: str) -> None:
        """Genera y asigna el hash de la contraseña."""
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica la contraseña contra el hash almacenado."""
        return check_password_hash(self.password, password)

    @classmethod
    def create(cls, **kwargs):
        """
        Sobrescribe el método `create` para hashear la contraseña antes de guardar.
        """
        if 'password' in kwargs:
            kwargs['password'] = generate_password_hash(kwargs['password'])
        return super().create(**kwargs)

    def update(self, commit=True, **kwargs):
        """
        Sobrescribe el método `update` para hashear la contraseña si se proporciona.
        """
        if 'password' in kwargs:
            kwargs['password'] = generate_password_hash(kwargs['password'])
        return super().update(commit=commit, **kwargs)

    def to_namespace_dict(self, include_relations=False, depth=1, fields=None):
        """
        Sobrescribe para asegurar que el campo 'password' nunca se serialize.
        """
        data = super().to_namespace_dict(include_relations, depth, fields)
        data.pop('password', None) # Eliminar el hash de la contraseña de la respuesta
        return data

    def __repr__(self):
        return f'<User {self.id}: {self.fullname}>'
