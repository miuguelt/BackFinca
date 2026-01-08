from datetime import datetime
import logging

from app import db
from app.models.activity_log import ActivityLog
from sqlalchemy import text

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
        # Flush para garantizar created_at/id antes del agregado (sin commit todavía)
        db.session.flush()

        # Upsert agregado diario (evita scans en /stats, /summary, /filters)
        try:
            agg_date = (log_entry.created_at or datetime.utcnow()).date()
            actor_val = int(actor_id) if actor_id is not None else 0
            animal_val = int(animal_id) if animal_id is not None else 0

            dialect = None
            try:
                dialect = db.session.get_bind().dialect.name
            except Exception:
                dialect = None

            if dialect in ("mysql", "mariadb"):
                db.session.execute(
                    text(
                        """
                        INSERT INTO activity_daily_agg
                          (`date`, `actor_id`, `entity`, `action`, `severity`, `animal_id`, `count`, `created_at`, `updated_at`)
                        VALUES
                          (:date, :actor_id, :entity, :action, :severity, :animal_id, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP())
                        ON DUPLICATE KEY UPDATE
                          `count` = `count` + 1,
                          `updated_at` = UTC_TIMESTAMP()
                        """
                    ),
                    {
                        "date": agg_date,
                        "actor_id": actor_val,
                        "entity": str(entity),
                        "action": str(action),
                        "severity": str(severity or "info"),
                        "animal_id": animal_val,
                    },
                )
            else:
                # Fallback portable (tests/SQLite): read-modify-write
                from app.models.activity_daily_agg import ActivityDailyAgg

                row = (
                    ActivityDailyAgg.query.filter_by(
                        date=agg_date,
                        actor_id=actor_val,
                        entity=str(entity),
                        action=str(action),
                        severity=str(severity or "info"),
                        animal_id=animal_val,
                    )
                    .with_for_update(read=False)
                    .first()
                )
                if row:
                    row.count = int(row.count or 0) + 1
                else:
                    db.session.add(
                        ActivityDailyAgg(
                            date=agg_date,
                            actor_id=actor_val,
                            entity=str(entity),
                            action=str(action),
                            severity=str(severity or "info"),
                            animal_id=animal_val,
                            count=1,
                        )
                    )
        except Exception as agg_exc:
            logger.debug("No se pudo actualizar activity_daily_agg: %s", agg_exc, exc_info=True)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.debug("No se pudo registrar activity_log: %s", exc, exc_info=True)
