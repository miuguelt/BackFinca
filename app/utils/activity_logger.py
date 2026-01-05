from datetime import datetime
import logging

from app import db
from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def build_relations_from_instance(instance):
    relations = {}
    try:
        for col in instance.__table__.columns:
            name = col.name
            if name == 'id':
                continue
            if name.endswith('_id') or name in ('animal_id', 'user_id'):
                value = getattr(instance, name, None)
                if value is not None:
                    relations[name] = value
    except Exception:
        pass
    return relations


def _safe_actor_id(actor_id):
    if actor_id is None:
        return None
    try:
        return int(actor_id)
    except Exception:
        return actor_id


def log_activity_event(
    *,
    action,
    entity,
    entity_id=None,
    title=None,
    description=None,
    severity='info',
    relations=None,
    actor_id=None,
    animal_id=None,
):
    if not entity or entity in ('activity_log', 'activitylog', 'ActivityLog'):
        return

    if actor_id is None:
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request(optional=True)
            actor_id = get_jwt_identity()
        except Exception:
            actor_id = None

    actor_id = _safe_actor_id(actor_id)
    if animal_id is None and relations:
        animal_id = relations.get('animal_id')

    try:
        log_entry = ActivityLog(
            action=action,
            entity=entity,
            entity_id=entity_id,
            title=title,
            description=description,
            severity=severity,
            actor_id=actor_id,
            animal_id=animal_id,
            relations=relations or None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.debug("No se pudo registrar activity_log: %s", exc, exc_info=True)
