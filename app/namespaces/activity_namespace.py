from datetime import datetime, timezone

from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields

from app.models.activity_log import ActivityLog
from app.utils.response_handler import APIResponse


activity_ns = Namespace(
    'activity',
    description='Activity feed endpoints',
    path='/activity'
)

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


def _format_activity(item):
    actor = None
    if item.actor:
        actor = {
            'id': item.actor.id,
            'fullname': item.actor.fullname,
        }
    return {
        'id': item.id,
        'action': item.action,
        'entity': item.entity,
        'entity_id': item.entity_id,
        'title': item.title,
        'description': item.description,
        'severity': item.severity,
        'created_at': item.created_at,
        'actor': actor,
        'relations': item.relations or {},
        'animal_id': item.animal_id,
    }


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

    from_dt = _parse_datetime(from_value)
    to_dt = _parse_datetime(to_value)
    if from_dt:
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        query = query.filter(ActivityLog.created_at >= from_dt)
    if to_dt:
        if to_dt.tzinfo is None:
            to_dt = to_dt.replace(tzinfo=timezone.utc)
        query = query.filter(ActivityLog.created_at <= to_dt)

    return query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())


@activity_ns.route('')
class ActivityList(Resource):
    @activity_ns.doc(
        'get_activity',
        description='Get paginated activity feed',
        params={
            'page': 'Page number',
            'limit': 'Items per page',
            'per_page': 'Items per page (alias)',
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
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50

        query = _build_query()
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [_format_activity(item) for item in pagination.items]

        return APIResponse.paginated_success(
            data=items,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Actividad obtenida'
        )

