from app import db
import enum
from app.models.base_model import BaseModel, ValidationError

class LandStatus(enum.Enum):
    """Estados posibles para los campos/potreros"""
    Disponible = "Disponible"
    Ocupado = "Ocupado"
    Mantenimiento = "Mantenimiento"
    Restringido = "Restringido"
    Dañado = "Dañado"
    Activo = "Activo"
    
    @classmethod
    def get_choices(cls):
        return [(choice.value, choice.value) for choice in cls]
        
    def __str__(self):
        """Devuelve el valor como string para facilitar la conversión"""
        return str(self.value)
        
    def __repr__(self):
        """Representación detallada para debug"""
        return f"{self.__class__.__name__}.{self.name}"

class Fields(BaseModel):
    """Modelo para campos/potreros de la finca optimizado para namespaces"""
    __tablename__ = "fields"
    
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    # NOTE: DB schema enforces NOT NULL for several columns; keep model aligned to avoid 409 IntegrityErrors.
    ubication = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.String(255), nullable=False)
    state = db.Column(db.Enum(LandStatus), nullable=False, default=LandStatus.Activo)
    handlings = db.Column(db.String(255), nullable=False)
    gauges = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(255), nullable=False, default="0")
    food_type_id = db.Column(db.Integer, db.ForeignKey('food_types.id'), nullable=False)

    # Configuración específica para namespaces
    _namespace_fields = ['id', 'name', 'ubication', 'capacity', 'state', 'handlings', 'gauges', 'area', 'food_type_id', 'animal_count', 'created_at']
    _namespace_relations = {
        'food_types': {'fields': ['id', 'food_type', 'handlings'], 'depth': 1},
        'animal_fields': {'fields': ['id', 'animal_id'], 'depth': 1}
    }
    _searchable_fields = ['name', 'ubication', 'handlings']
    _filterable_fields = ['state', 'food_type_id', 'capacity', 'area', 'created_at']
    _sortable_fields = ['id', 'name', 'capacity', 'area', 'created_at', 'updated_at']
    # Required fields aligned with DB NOT NULL constraints
    _required_fields = ['name', 'state', 'area', 'ubication', 'capacity', 'handlings', 'gauges', 'food_type_id']
    _unique_fields = ['name']
    _enum_fields = {'state': LandStatus}

    # Relaciones optimizadas
    animal_fields = db.relationship('AnimalFields', back_populates='field', lazy='dynamic')
    food_types = db.relationship('FoodTypes', back_populates='fields', lazy='selectin')

    def to_namespace_dict(self, include_relations=False, depth=1, fields=None):
        """Override para agregar cantidad de animales asignados al campo.

        Acepta y propaga "depth" y "fields" para mantener compatibilidad con BaseModel.
        """
        # Obtener el diccionario base del método padre respetando profundidad y selección de campos
        data = super().to_namespace_dict(include_relations=include_relations, depth=depth, fields=fields)

        # Agregar conteo de animales actualmente asignados a este campo
        # Usa la relación lazy='dynamic' que ya está optimizada
        prefetched = getattr(self, "_prefetched_animal_count", None)
        if prefetched is not None:
            animal_count = prefetched
        else:
            animal_count = self.animal_fields.filter_by(removal_date=None).count()

        data['animal_count'] = animal_count

        return data

    @classmethod
    def get_paginated_response(cls, query_result, include_relations=False, depth=1):
        """Optimiza serialización de listados precargando animal_count en 1 query.

        Evita N+1 queries cuando Fields.to_namespace_dict calcula conteos por instancia.
        """
        # Obtener instancias
        if hasattr(query_result, "items"):
            instances = list(query_result.items)
        else:
            instances = list(query_result)

        # Precargar conteos de animales activos por campo en una sola consulta
        try:
            from sqlalchemy import func
            from app.models.animalFields import AnimalFields

            field_ids = [inst.id for inst in instances if getattr(inst, "id", None) is not None]
            counts = {}
            if field_ids:
                rows = (
                    db.session.query(AnimalFields.field_id, func.count(AnimalFields.id))
                    .filter(AnimalFields.field_id.in_(field_ids), AnimalFields.removal_date.is_(None))
                    .group_by(AnimalFields.field_id)
                    .all()
                )
                counts = {fid: int(cnt) for fid, cnt in rows}

            for inst in instances:
                if getattr(inst, "id", None) is not None:
                    inst._prefetched_animal_count = counts.get(inst.id, 0)
        except Exception:
            pass

        items = [inst.to_namespace_dict(include_relations=include_relations, depth=depth) for inst in instances]

        if hasattr(query_result, "items"):
            return {
                "items": items,
                # legacy keys
                "total": query_result.total,
                "page": query_result.page,
                "per_page": query_result.per_page,
                "pages": query_result.pages,
                "has_next": query_result.has_next,
                "has_prev": query_result.has_prev,
                # new unified keys
                "total_items": query_result.total,
                "limit": query_result.per_page,
                "total_pages": query_result.pages,
                "has_next_page": query_result.has_next,
                "has_previous_page": query_result.has_prev,
            }

        return {
            "items": items,
            # legacy keys
            "total": len(items),
            "page": 1,
            "per_page": len(items),
            "pages": 1,
            "has_next": False,
            "has_prev": False,
            # new unified keys
            "total_items": len(items),
            "limit": len(items),
            "total_pages": 1,
            "has_next_page": False,
            "has_previous_page": False,
        }

    def __repr__(self):
        return f'<Field {self.id}: {self.name}>'
