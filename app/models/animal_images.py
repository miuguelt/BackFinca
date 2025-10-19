from app import db
from app.models.base_model import BaseModel
from datetime import datetime

class AnimalImages(BaseModel):
    """Modelo para imágenes de animales"""
    __tablename__ = 'animal_images'

    # Índices de rendimiento
    __table_args__ = (
        db.Index('ix_animal_images_animal_id', 'animal_id'),
        db.Index('ix_animal_images_is_primary', 'is_primary'),
        db.Index('ix_animal_images_created_at', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Tamaño en bytes
    mime_type = db.Column(db.String(100), nullable=True)  # ej: image/jpeg
    is_primary = db.Column(db.Boolean, default=False, nullable=False)  # Imagen principal del animal

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'animal_id', 'filename', 'filepath', 'file_size', 'mime_type', 'is_primary', 'created_at', 'updated_at']
    _namespace_relations = {
        'animal': {'fields': ['id', 'record', 'sex'], 'depth': 1}
    }
    _searchable_fields = ['filename']
    _filterable_fields = ['animal_id', 'is_primary', 'mime_type', 'created_at']
    _sortable_fields = ['id', 'filename', 'created_at', 'is_primary']
    _required_fields = ['animal_id', 'filename', 'filepath']

    # Relación con Animals
    animal = db.relationship('Animals', back_populates='images', lazy='selectin')

    @classmethod
    def _validate_and_normalize(cls, data, is_update=False, instance_id=None):
        """Validaciones específicas para imágenes de animales"""
        errors = []

        # Validar que el animal existe
        if 'animal_id' in data and data['animal_id']:
            from app.models.animals import Animals
            animal = Animals.query.get(data['animal_id'])
            if not animal:
                errors.append(f"El animal con ID {data['animal_id']} no existe")

        if errors:
            from app.models.base_model import ValidationError
            raise ValidationError('; '.join(errors), code="validation_error")

        # Llamar a la validación base
        return super()._validate_and_normalize(data, is_update, instance_id)

    def to_namespace_dict(self, include_relations=False, depth=1, fields=None):
        """Añade URL pública a la serialización (dinámica por origen)."""
        data = super().to_namespace_dict(include_relations, depth, fields)
        from app.utils.file_storage import get_public_url
        data['url'] = get_public_url(self.filepath)
        return data

    def __repr__(self):
        return f'<AnimalImage {self.id}: {self.filename}>'
