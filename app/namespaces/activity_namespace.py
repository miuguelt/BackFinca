import base64
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone

from flask import current_app, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload, load_only

from app import db
from app.models.activity_daily_agg import ActivityDailyAgg
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.utils.cache_utils import build_cache_key, cached_json_with_etag
from app.utils.response_handler import APIResponse


activity_ns = Namespace(
    'activity',
    description='Activity feed endpoints',
    path='/activity'
)

logger = logging.getLogger(__name__)

limiter = None


def set_limiter(app_limiter):
    """
    Aplicar rate limits específicos a endpoints caros de activity.
    Se llama desde app.api.register_api.
    """
    global limiter
    limiter = app_limiter
    try:
        if not limiter:
            return
        from app.utils.rate_limiter import RATE_LIMIT_CONFIG, get_remote_address_with_forwarded
        cfg = RATE_LIMIT_CONFIG.get('activity', {}) or {}
        summary_limit = cfg.get('summary', RATE_LIMIT_CONFIG.get('general', {}).get('read', "500 per hour"))
        stats_limit = cfg.get('stats', RATE_LIMIT_CONFIG.get('general', {}).get('read', "500 per hour"))
        filters_limit = cfg.get('filters', RATE_LIMIT_CONFIG.get('general', {}).get('read', "500 per hour"))

        for cls, limit_str in (
            (MyActivitySummary, summary_limit),
            (MyActivityStats, stats_limit),
            (ActivityStats, stats_limit),
            (ActivityFilters, filters_limit),
        ):
            func_obj = getattr(cls, "get", None)
            if not func_obj or getattr(func_obj, "_rate_limit_applied", False):
                continue
            wrapped = limiter.limit(limit_str, key_func=get_remote_address_with_forwarded, methods=["GET"])(func_obj)
            wrapped._rate_limit_applied = True
            setattr(cls, "get", wrapped)
        logger.info("Rate limits aplicados a activity endpoints")
    except Exception:
        logger.exception("No se pudo aplicar rate limiting a activity endpoints")

actor_model = activity_ns.model('ActivityActor', {
    'id': fields.Integer,
    'fullname': fields.String,
})

activity_model = activity_ns.model('ActivityItem', {
    'id': fields.Integer,
    'action': fields.String,
    'entity': fields.String,
    'entity_id': fields.Integer,
    'title': fields.String,
    'description': fields.String,
    'severity': fields.String,
    'created_at': fields.DateTime,
    'actor': fields.Nested(actor_model),
    'relations': fields.Raw,
    'animal_id': fields.Integer,
})

activity_meta_model = activity_ns.model('ActivityMeta', {
    'window': fields.Raw(description='Window configuration (from/to/days)'),
    'totals': fields.Raw(description='Totals (events, distinct_entities, distinct_animals)'),
    'by_entity': fields.Raw(description='Counts grouped by entity'),
    'by_action': fields.Raw(description='Counts grouped by action'),
    'by_severity': fields.Raw(description='Counts grouped by severity'),
    'daily': fields.Raw(description='Daily counts for trend charts'),
})

activity_summary_model = activity_ns.model('ActivitySummary', {
    'user_id': fields.Integer,
    'last_activity_at': fields.DateTime,
    'window_7d': fields.Nested(activity_meta_model),
    'window_30d': fields.Nested(activity_meta_model),
})


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        return datetime.fromisoformat(text)
    except Exception:
        try:
            return datetime.strptime(text, '%Y-%m-%d')
        except Exception:
            return None


def _safe_int(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except Exception:
        return None


def _iso(dt):
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    try:
        # Treat naive datetimes as UTC
        if getattr(dt, 'tzinfo', None) is None:
            return dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except Exception:
        return None


def _parse_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    parts = [p.strip() for p in str(value).split(",")]
    return {p for p in parts if p}


def _normalize_dt_for_db(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _format_activity(item, *, include_actor=True, include_relations=True, fields_set: set[str] | None = None):
    actor = None
    if include_actor and getattr(item, "actor", None):
        actor = {
            'id': item.actor.id,
            'fullname': item.actor.fullname,
        }
    payload = {
        'id': item.id,
        'action': item.action,
        'entity': item.entity,
        'entity_id': item.entity_id,
        'title': item.title,
        'description': item.description,
        'severity': item.severity,
        'created_at': _iso(item.created_at),
        'actor': actor if include_actor else None,
        'relations': (item.relations or {}) if include_relations else None,
        'animal_id': item.animal_id,
    }
    if not include_actor:
        payload.pop("actor", None)
    if not include_relations:
        payload.pop("relations", None)
    if fields_set:
        payload = {k: payload.get(k) for k in fields_set if k in payload}
    return payload


def _encode_cursor(created_at: datetime, row_id: int) -> str:
    raw = json.dumps(
        {"created_at": _iso(created_at), "id": int(row_id)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[datetime | None, int | None]:
    if not cursor:
        return None, None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        dt = _parse_datetime(data.get("created_at"))
        return _normalize_dt_for_db(dt), _safe_int(data.get("id"))
    except Exception:
        return None, None


def _activity_load_only(fields_set: set[str] | None, *, include_actor: bool, include_relations: bool):
    # Always load keys required for ordering/cursor
    wanted = {"id", "created_at"}
    if fields_set:
        wanted |= set(fields_set)
    else:
        wanted |= {"action", "entity", "entity_id", "title", "description", "severity", "animal_id", "relations", "actor"}

    cols = [ActivityLog.id, ActivityLog.created_at]
    if "action" in wanted:
        cols.append(ActivityLog.action)
    if "entity" in wanted:
        cols.append(ActivityLog.entity)
    if "entity_id" in wanted:
        cols.append(ActivityLog.entity_id)
    if "title" in wanted:
        cols.append(ActivityLog.title)
    if "description" in wanted:
        cols.append(ActivityLog.description)
    if "severity" in wanted:
        cols.append(ActivityLog.severity)
    if "animal_id" in wanted:
        cols.append(ActivityLog.animal_id)
    if include_relations or ("relations" in wanted):
        cols.append(ActivityLog.relations)
    if include_actor:
        cols.append(ActivityLog.actor_id)
    return cols


def _build_query(user_id=None):
    query = ActivityLog.query

    entity = request.args.get('entity')
    action = request.args.get('action')
    severity = request.args.get('severity')
    entity_id = request.args.get('entity_id', type=int)
    actor_id = request.args.get('user_id', type=int)
    animal_id = request.args.get('animal_id', type=int)
    from_value = request.args.get('from')
    to_value = request.args.get('to')

    if user_id is not None:
        query = query.filter(ActivityLog.actor_id == user_id)
    elif actor_id is not None:
        query = query.filter(ActivityLog.actor_id == actor_id)

    if entity:
        query = query.filter(ActivityLog.entity == entity)
    if action:
        query = query.filter(ActivityLog.action == action)
    if severity:
        query = query.filter(ActivityLog.severity == severity)
    if entity_id is not None:
        query = query.filter(ActivityLog.entity_id == entity_id)
    if animal_id is not None:
        query = query.filter(ActivityLog.animal_id == animal_id)

    from_dt = _normalize_dt_for_db(_parse_datetime(from_value))
    to_dt = _normalize_dt_for_db(_parse_datetime(to_value))
    if from_dt:
        query = query.filter(ActivityLog.created_at >= from_dt)
    if to_dt:
        query = query.filter(ActivityLog.created_at <= to_dt)

    return query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())


def _window_bounds(days: int | None = None):
    from_value = request.args.get('from')
    to_value = request.args.get('to')

    from_dt = _parse_datetime(from_value)
    to_dt = _parse_datetime(to_value)
    if days and not from_dt and not to_dt:
        to_dt = datetime.now(timezone.utc)
        from_dt = to_dt - timedelta(days=int(days))

    if from_dt and from_dt.tzinfo is None:
        from_dt = from_dt.replace(tzinfo=timezone.utc)
    if to_dt and to_dt.tzinfo is None:
        to_dt = to_dt.replace(tzinfo=timezone.utc)
    return from_dt, to_dt


def _apply_bounds(query, from_dt, to_dt):
    if from_dt:
        if getattr(from_dt, 'tzinfo', None) is not None:
            from_dt = from_dt.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(ActivityLog.created_at >= from_dt)
    if to_dt:
        if getattr(to_dt, 'tzinfo', None) is not None:
            to_dt = to_dt.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(ActivityLog.created_at <= to_dt)
    return query


def _stats_payload(base_query, *, from_dt, to_dt, window_days: int | None = None):
    # Totals
    totals = base_query.with_entities(
        func.count(ActivityLog.id),
        func.count(func.distinct(ActivityLog.entity)),
        func.count(func.distinct(ActivityLog.animal_id)),
    ).first()

    # Groupings
    by_entity = (
        base_query.with_entities(ActivityLog.entity.label('key'), func.count(ActivityLog.id).label('count'))
        .group_by(ActivityLog.entity)
        .order_by(func.count(ActivityLog.id).desc(), ActivityLog.entity.asc())
        .all()
    )
    by_action = (
        base_query.with_entities(ActivityLog.action.label('key'), func.count(ActivityLog.id).label('count'))
        .group_by(ActivityLog.action)
        .order_by(func.count(ActivityLog.id).desc(), ActivityLog.action.asc())
        .all()
    )
    by_severity = (
        base_query.with_entities(ActivityLog.severity.label('key'), func.count(ActivityLog.id).label('count'))
        .group_by(ActivityLog.severity)
        .order_by(func.count(ActivityLog.id).desc(), ActivityLog.severity.asc())
        .all()
    )

    # Trend (group by day) - MySQL compatible (DATE(datetime))
    daily = (
        base_query.with_entities(func.date(ActivityLog.created_at).label('day'), func.count(ActivityLog.id).label('count'))
        .group_by(func.date(ActivityLog.created_at))
        .order_by(func.date(ActivityLog.created_at).asc())
        .all()
    )

    window = {
        'days': int(window_days) if window_days else None,
        'from': from_dt.isoformat().replace('+00:00', 'Z') if from_dt else None,
        'to': to_dt.isoformat().replace('+00:00', 'Z') if to_dt else None,
    }

    return {
        'window': window,
        'totals': {
            'events': int(totals[0] or 0),
            'distinct_entities': int(totals[1] or 0),
            'distinct_animals': int(totals[2] or 0),
        },
        'by_entity': [{'entity': row.key, 'count': int(row.count)} for row in by_entity],
        'by_action': [{'action': row.key, 'count': int(row.count)} for row in by_action],
        'by_severity': [{'severity': row.key, 'count': int(row.count)} for row in by_severity],
        'daily': [{'date': (row.day.isoformat() if row.day else None), 'count': int(row.count)} for row in daily],
    }


def _window_date_bounds(days: int | None):
    from_dt, to_dt = _window_bounds(days)
    from_dt = _normalize_dt_for_db(from_dt)
    to_dt = _normalize_dt_for_db(to_dt)

    now = datetime.utcnow()
    if not to_dt:
        to_dt = now
    if not from_dt and days:
        from_dt = to_dt - timedelta(days=int(days))

    start_date = (from_dt or (to_dt - timedelta(days=int(days or 30)))).date()
    end_date = (to_dt or now).date()
    return start_date, end_date, from_dt, to_dt


def _can_use_daily_agg(from_dt, to_dt) -> bool:
    if request.args.get("entity_id"):
        return False
    # daily agg cannot do exact time ranges; fallback when time is used
    if from_dt and (from_dt.hour or from_dt.minute or from_dt.second or from_dt.microsecond):
        return False
    if to_dt and (to_dt.hour or to_dt.minute or to_dt.second or to_dt.microsecond):
        return False
    return True


def _agg_stats_payload(*, actor_id: int | None, start_date: date, end_date: date, days: int | None):
    base = db.session.query(ActivityDailyAgg).filter(
        ActivityDailyAgg.date >= start_date,
        ActivityDailyAgg.date <= end_date,
    )
    if actor_id is not None:
        base = base.filter(ActivityDailyAgg.actor_id == int(actor_id))

    entity = request.args.get("entity")
    action = request.args.get("action")
    severity = request.args.get("severity")
    animal_id = request.args.get("animal_id", type=int)
    if entity:
        base = base.filter(ActivityDailyAgg.entity == entity)
    if action:
        base = base.filter(ActivityDailyAgg.action == action)
    if severity:
        base = base.filter(ActivityDailyAgg.severity == severity)
    if animal_id is not None:
        base = base.filter(ActivityDailyAgg.animal_id == int(animal_id))

    totals_events = base.with_entities(func.coalesce(func.sum(ActivityDailyAgg.count), 0)).scalar() or 0
    distinct_entities = base.with_entities(func.count(func.distinct(ActivityDailyAgg.entity))).scalar() or 0
    distinct_animals = (
        base.filter(ActivityDailyAgg.animal_id != 0)
        .with_entities(func.count(func.distinct(ActivityDailyAgg.animal_id)))
        .scalar()
        or 0
    )

    by_entity = (
        base.with_entities(ActivityDailyAgg.entity.label("key"), func.sum(ActivityDailyAgg.count).label("count"))
        .group_by(ActivityDailyAgg.entity)
        .order_by(func.sum(ActivityDailyAgg.count).desc(), ActivityDailyAgg.entity.asc())
        .all()
    )
    by_action = (
        base.with_entities(ActivityDailyAgg.action.label("key"), func.sum(ActivityDailyAgg.count).label("count"))
        .group_by(ActivityDailyAgg.action)
        .order_by(func.sum(ActivityDailyAgg.count).desc(), ActivityDailyAgg.action.asc())
        .all()
    )
    by_severity = (
        base.with_entities(ActivityDailyAgg.severity.label("key"), func.sum(ActivityDailyAgg.count).label("count"))
        .group_by(ActivityDailyAgg.severity)
        .order_by(func.sum(ActivityDailyAgg.count).desc(), ActivityDailyAgg.severity.asc())
        .all()
    )
    daily = (
        base.with_entities(ActivityDailyAgg.date.label("day"), func.sum(ActivityDailyAgg.count).label("count"))
        .group_by(ActivityDailyAgg.date)
        .order_by(ActivityDailyAgg.date.asc())
        .all()
    )

    window = {
        "days": int(days) if days else None,
        "from": f"{start_date.isoformat()}T00:00:00Z" if start_date else None,
        "to": f"{end_date.isoformat()}T23:59:59Z" if end_date else None,
    }
    return {
        "window": window,
        "totals": {
            "events": int(totals_events),
            "distinct_entities": int(distinct_entities),
            "distinct_animals": int(distinct_animals),
        },
        "by_entity": [{"entity": row.key, "count": int(row.count)} for row in by_entity],
        "by_action": [{"action": row.key, "count": int(row.count)} for row in by_action],
        "by_severity": [{"severity": row.key, "count": int(row.count)} for row in by_severity],
        "daily": [{"date": (row.day.isoformat() if row.day else None), "count": int(row.count)} for row in daily],
    }


def _make_cached_response(cache_key: str, ttl_seconds: int, compute_fn, *, private=True):
    payload, status, headers = cached_json_with_etag(
        cache_key=cache_key,
        ttl_seconds=int(ttl_seconds),
        compute=compute_fn,
        private=private,
    )
    resp = make_response(jsonify(payload) if status != 304 else "", status)
    for k, v in (headers or {}).items():
        resp.headers[k] = v
    return resp


@activity_ns.route('/me')
class MyActivityList(Resource):
    @activity_ns.doc(
        'get_my_activity',
        description='Get paginated activity feed for the authenticated user',
        security=['Bearer', 'Cookie'],
        params={
            'cursor': 'Keyset cursor (base64). If set, uses keyset pagination.',
            'cursor_mode': 'If 1, use keyset pagination and return next_cursor',
            'page': 'Page number',
            'limit': 'Items per page',
            'per_page': 'Items per page (alias)',
            'include': 'Comma list: actor,relations (default: both)',
            'fields': 'Comma list of fields to return (restrict payload)',
            'entity': 'Filter by entity',
            'action': 'Filter by action',
            'severity': 'Filter by severity',
            'entity_id': 'Filter by entity id',
            'animal_id': 'Filter by animal id',
            'from': 'ISO datetime lower bound',
            'to': 'ISO datetime upper bound',
        }
    )
    @jwt_required()
    def get(self):
        user_id = _safe_int(get_jwt_identity())
        include_set = _parse_csv(request.args.get("include"))
        fields_set = _parse_csv(request.args.get("fields")) or None
        include_actor = True if not include_set else ("actor" in include_set)
        include_relations = True if not include_set else ("relations" in include_set)

        cursor = request.args.get("cursor")
        cursor_mode = request.args.get("cursor_mode")
        use_cursor = bool(cursor) or str(cursor_mode) in ("1", "true", "True")
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        limit = min(max(int(limit), 1), 200)

        query = _build_query(user_id=user_id)
        query = query.options(load_only(*_activity_load_only(fields_set, include_actor=include_actor, include_relations=include_relations)))
        if include_actor:
            query = query.options(joinedload(ActivityLog.actor).load_only(User.id, User.fullname))

        if use_cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            if cursor_dt and cursor_id:
                query = query.filter(
                    or_(
                        ActivityLog.created_at < cursor_dt,
                        and_(ActivityLog.created_at == cursor_dt, ActivityLog.id < cursor_id),
                    )
                )
            rows = query.limit(limit + 1).all()
            has_more = len(rows) > limit
            rows = rows[:limit]
            items = [
                _format_activity(r, include_actor=include_actor, include_relations=include_relations, fields_set=fields_set)
                for r in rows
            ]
            next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if rows and has_more else None
            body, status = APIResponse.success(
                data={"items": items, "next_cursor": next_cursor, "has_more": has_more, "limit": limit},
                message="Actividad del usuario obtenida",
            )
            resp = make_response(jsonify(body), status)
            resp.headers["X-Has-More"] = "1" if has_more else "0"
            return resp

        page = request.args.get('page', default=1, type=int) or 1
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [
            _format_activity(r, include_actor=include_actor, include_relations=include_relations, fields_set=fields_set)
            for r in pagination.items
        ]
        return APIResponse.paginated_success(
            data=items,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Actividad del usuario obtenida'
        )


@activity_ns.route('/stats')
class ActivityStats(Resource):
    @activity_ns.doc(
        'get_activity_stats',
        description='Get aggregated stats for the activity feed (global or filtered by query params). Use /activity/me/stats for per-user.',
        security=['Bearer', 'Cookie'],
        params={
            'days': 'Window in days (default 30 if from/to not provided)',
            'entity': 'Filter by entity',
            'action': 'Filter by action',
            'severity': 'Filter by severity',
            'entity_id': 'Filter by entity id',
            'user_id': 'Filter by actor user id',
            'animal_id': 'Filter by animal id',
            'from': 'ISO datetime lower bound',
            'to': 'ISO datetime upper bound',
        }
    )
    @jwt_required()
    def get(self):
        window_days = request.args.get('days', default=30, type=int)
        start_date, end_date, from_dt, to_dt = _window_date_bounds(window_days)
        actor_id = request.args.get("user_id", type=int)
        requester_id = _safe_int(get_jwt_identity())
        ttl = int(current_app.config.get("ACTIVITY_STATS_CACHE_TTL", 60))

        cache_key = build_cache_key(
            "activity:stats:v2",
            {
                "requester": requester_id,
                "actor_id": actor_id,
                "days": int(window_days) if window_days else None,
                "from": request.args.get("from"),
                "to": request.args.get("to"),
                "entity": request.args.get("entity"),
                "action": request.args.get("action"),
                "severity": request.args.get("severity"),
                "animal_id": request.args.get("animal_id"),
                "entity_id": request.args.get("entity_id"),
            },
        )

        def compute():
            t0 = time.perf_counter()
            if _can_use_daily_agg(from_dt, to_dt):
                try:
                    payload = _agg_stats_payload(actor_id=actor_id, start_date=start_date, end_date=end_date, days=window_days)
                except Exception:
                    logger.debug("Fallback a stats raw (agg no disponible)", exc_info=True)
                    base = _build_query()
                    base = _apply_bounds(base, from_dt, to_dt).order_by(None)
                    payload = _stats_payload(base, from_dt=from_dt, to_dt=to_dt, window_days=window_days)
            else:
                base = _build_query()
                base = _apply_bounds(base, from_dt, to_dt).order_by(None)
                payload = _stats_payload(base, from_dt=from_dt, to_dt=to_dt, window_days=window_days)
            body, _ = APIResponse.success(data=payload, message="Estadísticas de actividad obtenidas")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > 250:
                logger.info("activity.stats slow path %.1fms key=%s", elapsed_ms, cache_key[:80])
            return body

        return _make_cached_response(cache_key, ttl, compute, private=True)


@activity_ns.route('/me/stats')
class MyActivityStats(Resource):
    @activity_ns.doc(
        'get_my_activity_stats',
        description='Get aggregated stats for the authenticated user activity feed.',
        security=['Bearer', 'Cookie'],
        params={
            'days': 'Window in days (default 30 if from/to not provided)',
            'entity': 'Filter by entity',
            'action': 'Filter by action',
            'severity': 'Filter by severity',
            'entity_id': 'Filter by entity id',
            'animal_id': 'Filter by animal id',
            'from': 'ISO datetime lower bound',
            'to': 'ISO datetime upper bound',
        }
    )
    @jwt_required()
    def get(self):
        user_id = _safe_int(get_jwt_identity())
        window_days = request.args.get('days', default=30, type=int)
        start_date, end_date, from_dt, to_dt = _window_date_bounds(window_days)
        ttl = int(current_app.config.get("ACTIVITY_STATS_CACHE_TTL", 60))

        cache_key = build_cache_key(
            "activity:me:stats:v2",
            {
                "user_id": user_id,
                "days": int(window_days) if window_days else None,
                "from": request.args.get("from"),
                "to": request.args.get("to"),
                "entity": request.args.get("entity"),
                "action": request.args.get("action"),
                "severity": request.args.get("severity"),
                "animal_id": request.args.get("animal_id"),
                "entity_id": request.args.get("entity_id"),
            },
        )

        def compute():
            t0 = time.perf_counter()
            if _can_use_daily_agg(from_dt, to_dt):
                try:
                    payload = _agg_stats_payload(actor_id=user_id, start_date=start_date, end_date=end_date, days=window_days)
                except Exception:
                    logger.debug("Fallback a my stats raw (agg no disponible)", exc_info=True)
                    base = _build_query(user_id=user_id)
                    base = _apply_bounds(base, from_dt, to_dt).order_by(None)
                    payload = _stats_payload(base, from_dt=from_dt, to_dt=to_dt, window_days=window_days)
            else:
                base = _build_query(user_id=user_id)
                base = _apply_bounds(base, from_dt, to_dt).order_by(None)
                payload = _stats_payload(base, from_dt=from_dt, to_dt=to_dt, window_days=window_days)
            body, _ = APIResponse.success(data=payload, message="Estadísticas de actividad del usuario obtenidas")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > 250:
                logger.info("activity.me.stats slow path %.1fms key=%s", elapsed_ms, cache_key[:80])
            return body

        return _make_cached_response(cache_key, ttl, compute, private=True)


@activity_ns.route('/me/summary')
class MyActivitySummary(Resource):
    @activity_ns.doc(
        'get_my_activity_summary',
        description='Get a ready-to-render summary for the profile "Tu actividad" area (7d + 30d stats).',
        security=['Bearer', 'Cookie'],
    )
    @jwt_required()
    def get(self):
        user_id = _safe_int(get_jwt_identity())
        ttl = int(current_app.config.get("ACTIVITY_SUMMARY_CACHE_TTL", 60))
        cache_key = build_cache_key("activity:me:summary:v3", {"user_id": user_id})

        def compute():
            t0 = time.perf_counter()

            # Last activity timestamp (uses composite index actor_id,created_at)
            last_dt = (
                ActivityLog.query.with_entities(func.max(ActivityLog.created_at))
                .filter(ActivityLog.actor_id == user_id)
                .scalar()
            )

            # Single query from daily agg for last 30 days; compute 7d/30d in Python
            end_date = datetime.utcnow().date()
            start_30 = end_date - timedelta(days=30)
            start_7 = end_date - timedelta(days=7)

            try:
                rows = (
                    db.session.query(
                        ActivityDailyAgg.date,
                        ActivityDailyAgg.entity,
                        ActivityDailyAgg.action,
                        ActivityDailyAgg.severity,
                        ActivityDailyAgg.animal_id,
                        ActivityDailyAgg.count,
                    )
                    .filter(
                        ActivityDailyAgg.actor_id == int(user_id),
                        ActivityDailyAgg.date >= start_30,
                        ActivityDailyAgg.date <= end_date,
                    )
                    .all()
                )
            except Exception:
                logger.debug("Fallback a summary raw (agg no disponible)", exc_info=True)
                from_7, to_7 = _window_bounds(7)
                base_7 = ActivityLog.query.filter(ActivityLog.actor_id == user_id)
                base_7 = _apply_bounds(base_7, from_7, to_7).order_by(None)
                stats_7 = _stats_payload(base_7, from_dt=from_7, to_dt=to_7, window_days=7)

                from_30, to_30 = _window_bounds(30)
                base_30 = ActivityLog.query.filter(ActivityLog.actor_id == user_id)
                base_30 = _apply_bounds(base_30, from_30, to_30).order_by(None)
                stats_30 = _stats_payload(base_30, from_dt=from_30, to_dt=to_30, window_days=30)

                body, _ = APIResponse.success(
                    data={
                        "user_id": user_id,
                        "last_activity_at": _iso(last_dt),
                        "window_7d": stats_7,
                        "window_30d": stats_30,
                    },
                    message="Resumen de actividad obtenido",
                )
                return body

            def compute_window(start_date_local: date, days_local: int):
                events = 0
                entities = set()
                animals = set()
                by_entity = {}
                by_action = {}
                by_severity = {}
                daily = {}

                for d, ent, act, sev, aid, cnt in rows:
                    if d < start_date_local:
                        continue
                    c = int(cnt or 0)
                    events += c
                    if ent:
                        entities.add(ent)
                        by_entity[ent] = by_entity.get(ent, 0) + c
                    if act:
                        by_action[act] = by_action.get(act, 0) + c
                    if sev:
                        by_severity[sev] = by_severity.get(sev, 0) + c
                    if aid and int(aid) != 0:
                        animals.add(int(aid))
                    daily[d] = daily.get(d, 0) + c

                return {
                    "window": {
                        "days": int(days_local),
                        "from": f"{start_date_local.isoformat()}T00:00:00Z",
                        "to": f"{end_date.isoformat()}T23:59:59Z",
                    },
                    "totals": {
                        "events": int(events),
                        "distinct_entities": int(len(entities)),
                        "distinct_animals": int(len(animals)),
                    },
                    "by_entity": [{"entity": k, "count": int(v)} for k, v in sorted(by_entity.items(), key=lambda x: (-x[1], x[0]))],
                    "by_action": [{"action": k, "count": int(v)} for k, v in sorted(by_action.items(), key=lambda x: (-x[1], x[0]))],
                    "by_severity": [{"severity": k, "count": int(v)} for k, v in sorted(by_severity.items(), key=lambda x: (-x[1], x[0]))],
                    "daily": [{"date": d.isoformat(), "count": int(v)} for d, v in sorted(daily.items(), key=lambda x: x[0])],
                }

            stats_30 = compute_window(start_30, 30)
            stats_7 = compute_window(start_7, 7)

            body, _ = APIResponse.success(
                data={
                    "user_id": user_id,
                    "last_activity_at": _iso(last_dt),
                    "window_7d": stats_7,
                    "window_30d": stats_30,
                },
                message="Resumen de actividad obtenido",
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > 250:
                logger.info("activity.me.summary slow path %.1fms key=%s", elapsed_ms, cache_key[:80])
            return body

        return _make_cached_response(cache_key, ttl, compute, private=True)


@activity_ns.route('/filters')
class ActivityFilters(Resource):
    @activity_ns.doc(
        'get_activity_filters',
        description='Get distinct values for filters (entities/actions/severities) to build UI dropdowns.',
        security=['Bearer', 'Cookie'],
        params={
            'scope': 'me|global (default: me)',
            'days': 'Window in days (default 365 if from/to not provided)',
            'from': 'ISO datetime lower bound',
            'to': 'ISO datetime upper bound',
        }
    )
    @jwt_required()
    def get(self):
        requester_id = _safe_int(get_jwt_identity())
        scope = request.args.get("scope") or "me"
        window_days = request.args.get('days', default=365, type=int)
        start_date, end_date, _from_dt, _to_dt = _window_date_bounds(window_days)

        ttl = int(current_app.config.get("ACTIVITY_FILTERS_CACHE_TTL", 120))
        cache_key = build_cache_key(
            "activity:filters:v2",
            {
                "requester": requester_id,
                "scope": scope,
                "days": int(window_days) if window_days else None,
                "from": request.args.get("from"),
                "to": request.args.get("to"),
            },
        )

        def compute():
            t0 = time.perf_counter()
            try:
                base = db.session.query(ActivityDailyAgg).filter(
                    ActivityDailyAgg.date >= start_date,
                    ActivityDailyAgg.date <= end_date,
                )
                if scope != "global":
                    base = base.filter(ActivityDailyAgg.actor_id == int(requester_id))

                entities = [r[0] for r in base.with_entities(ActivityDailyAgg.entity).distinct().order_by(ActivityDailyAgg.entity.asc()).all()]
                actions = [r[0] for r in base.with_entities(ActivityDailyAgg.action).distinct().order_by(ActivityDailyAgg.action.asc()).all()]
                severities = [r[0] for r in base.with_entities(ActivityDailyAgg.severity).distinct().order_by(ActivityDailyAgg.severity.asc()).all()]
            except Exception:
                logger.debug("Fallback a filters raw (agg no disponible)", exc_info=True)
                from_dt, to_dt = _window_bounds(window_days)
                raw = _apply_bounds(ActivityLog.query, from_dt, to_dt).order_by(None)
                if scope != "global":
                    raw = raw.filter(ActivityLog.actor_id == int(requester_id))
                entities = [r[0] for r in raw.with_entities(ActivityLog.entity).distinct().order_by(ActivityLog.entity.asc()).all()]
                actions = [r[0] for r in raw.with_entities(ActivityLog.action).distinct().order_by(ActivityLog.action.asc()).all()]
                severities = [r[0] for r in raw.with_entities(ActivityLog.severity).distinct().order_by(ActivityLog.severity.asc()).all()]

            body, _ = APIResponse.success(
                data={
                    "window": {
                        "days": int(window_days) if window_days else None,
                        "from": f"{start_date.isoformat()}T00:00:00Z" if start_date else None,
                        "to": f"{end_date.isoformat()}T23:59:59Z" if end_date else None,
                    },
                    "scope": scope,
                    "entities": entities,
                    "actions": actions,
                    "severities": severities,
                },
                message="Filtros de actividad obtenidos",
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            if elapsed_ms > 250:
                logger.info("activity.filters slow path %.1fms key=%s", elapsed_ms, cache_key[:80])
            return body

        return _make_cached_response(cache_key, ttl, compute, private=True)


@activity_ns.route('')
class ActivityList(Resource):
    @activity_ns.doc(
        'get_activity',
        description='Get paginated activity feed',
        params={
            'cursor': 'Keyset cursor (base64). If set, uses keyset pagination.',
            'cursor_mode': 'If 1, use keyset pagination and return next_cursor',
            'page': 'Page number',
            'limit': 'Items per page',
            'per_page': 'Items per page (alias)',
            'include': 'Comma list: actor,relations (default: both)',
            'fields': 'Comma list of fields to return (restrict payload)',
            'entity': 'Filter by entity',
            'action': 'Filter by action',
            'severity': 'Filter by severity',
            'entity_id': 'Filter by entity id',
            'user_id': 'Filter by actor user id',
            'animal_id': 'Filter by animal id',
            'from': 'ISO datetime lower bound',
            'to': 'ISO datetime upper bound',
        }
    )
    @jwt_required()
    def get(self):
        include_set = _parse_csv(request.args.get("include"))
        fields_set = _parse_csv(request.args.get("fields")) or None
        include_actor = True if not include_set else ("actor" in include_set)
        include_relations = True if not include_set else ("relations" in include_set)

        cursor = request.args.get("cursor")
        cursor_mode = request.args.get("cursor_mode")
        use_cursor = bool(cursor) or str(cursor_mode) in ("1", "true", "True")
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50
        limit = min(max(int(limit), 1), 200)

        query = _build_query()
        query = query.options(load_only(*_activity_load_only(fields_set, include_actor=include_actor, include_relations=include_relations)))
        if include_actor:
            query = query.options(joinedload(ActivityLog.actor).load_only(User.id, User.fullname))

        if use_cursor:
            cursor_dt, cursor_id = _decode_cursor(cursor)
            if cursor_dt and cursor_id:
                query = query.filter(
                    or_(
                        ActivityLog.created_at < cursor_dt,
                        and_(ActivityLog.created_at == cursor_dt, ActivityLog.id < cursor_id),
                    )
                )
            rows = query.limit(limit + 1).all()
            has_more = len(rows) > limit
            rows = rows[:limit]
            items = [
                _format_activity(r, include_actor=include_actor, include_relations=include_relations, fields_set=fields_set)
                for r in rows
            ]
            next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if rows and has_more else None
            body, status = APIResponse.success(
                data={"items": items, "next_cursor": next_cursor, "has_more": has_more, "limit": limit},
                message="Actividad obtenida",
            )
            resp = make_response(jsonify(body), status)
            resp.headers["X-Has-More"] = "1" if has_more else "0"
            return resp

        page = request.args.get('page', default=1, type=int) or 1
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [
            _format_activity(r, include_actor=include_actor, include_relations=include_relations, fields_set=fields_set)
            for r in pagination.items
        ]
        return APIResponse.paginated_success(
            data=items,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Actividad obtenida'
        )
