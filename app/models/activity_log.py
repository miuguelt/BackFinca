from app import db
from app.models.base_model import BaseModel


class ActivityLog(BaseModel):
    __tablename__ = 'activity_log'
    __table_args__ = (
        db.Index('ix_activity_log_created_at', 'created_at'),
        db.Index('ix_activity_log_action', 'action'),
        db.Index('ix_activity_log_entity', 'entity'),
        db.Index('ix_activity_log_severity', 'severity'),
        db.Index('ix_activity_log_actor_id', 'actor_id'),
        db.Index('ix_activity_log_entity_id', 'entity_id'),
        db.Index('ix_activity_log_animal_id', 'animal_id'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action = db.Column(db.String(20), nullable=False)
    entity = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=False, default='info')
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    animal_id = db.Column(db.Integer, nullable=True)
    relations = db.Column(db.JSON, nullable=True)

    actor = db.relationship('User', foreign_keys=[actor_id], lazy='joined')

    _namespace_fields = [
        'id',
        'action',
        'entity',
        'entity_id',
        'title',
        'description',
        'severity',
        'actor_id',
        'animal_id',
        'relations',
        'created_at',
        'updated_at',
    ]
    _filterable_fields = [
        'action',
        'entity',
        'severity',
        'actor_id',
        'animal_id',
        'created_at',
    ]
    _searchable_fields = ['title', 'description']
    _sortable_fields = ['created_at', 'id']
    _required_fields = ['action', 'entity']

    def __repr__(self):
        return f'<ActivityLog {self.id}: {self.entity}:{self.action}>'
