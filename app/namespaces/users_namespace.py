
from flask_restx import Resource, fields
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.user import User, Role
from app.models.activity_log import ActivityLog
from app.utils.namespace_helpers import create_optimized_namespace
from app.utils.response_handler import APIResponse
from app import db
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

limiter = None

users_ns = create_optimized_namespace(
    name='users',
    description='👥 Gestión Optimizada de Usuarios del Sistema',
    model_class=User,
    path='/users',
    public_create=True,
)

# Configurar rate limiting específico para creación de usuarios (sólo POST /users)
def set_limiter(app_limiter):
    global limiter
    limiter = app_limiter
    try:
        if not limiter:
            return
        from app.utils.rate_limiter import RATE_LIMIT_CONFIG, get_remote_address_with_forwarded
        create_limit = (RATE_LIMIT_CONFIG.get('users', {}) or {}).get('create', "10 per hour")
        list_resource = getattr(users_ns, '_model_list_resource', None)
        if list_resource and hasattr(list_resource, 'post') and not getattr(list_resource.post, '_rate_limit_applied', False):
            list_resource.post = limiter.limit(create_limit, key_func=get_remote_address_with_forwarded, methods=["POST"])(list_resource.post)
            list_resource.post._rate_limit_applied = True
            logger.info("Rate limit aplicado a creación de usuarios: %s", create_limit)
    except Exception:
        logger.exception("No se pudo aplicar rate limit a creación de usuarios")

# El endpoint POST se crea automáticamente por create_optimized_namespace
# Configurado como ruta pública en security_middleware (sin JWT)

# Modelos Swagger para estadísticas (definir después de users_ns)
user_role_stats_model = users_ns.model('UserRoleStats', {
    'count': fields.Integer,
    'percentage': fields.Float
})
user_status_stats_model = users_ns.model('UserStatusStats', {
    'active_users': fields.Integer,
    'inactive_users': fields.Integer,
    'total_users': fields.Integer,
    'active_percentage': fields.Float
})
user_roles_distribution_model = users_ns.model('UserRolesDistribution', {
    'roles': fields.Raw,  # Dict[str, {count, percentage}]
    'total_users': fields.Integer
})
user_statistics_model = users_ns.model('UserStatistics', {
    'total_users': fields.Integer,
    'role_distribution': fields.Raw,
    'status_distribution': fields.Raw
})

# Definir rutas personalizadas adicionales
@users_ns.route('/statistics')
class UserStatistics(Resource):
    @users_ns.doc('get_user_statistics', description='Estadísticas completas de usuarios', security=['Bearer'])
    @jwt_required()
    def get(self):
        try:
            role_stats = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
            status_stats = db.session.query(User.status, func.count(User.id)).group_by(User.status).all()
            role_dict = {role.value: count for role, count in role_stats}
            status_dict = {status: count for status, count in status_stats}
            total_users = sum(role_dict.values())
            payload = {
                'total_users': total_users,
                'role_distribution': {
                    r: {
                        'count': role_dict.get(r, 0),
                        'percentage': round((role_dict.get(r, 0) / total_users * 100) if total_users else 0, 2)
                    } for r in ['Aprendiz', 'Instructor', 'Administrador']
                },
                'status_distribution': {
                    'active': status_dict.get(True, 0),
                    'inactive': status_dict.get(False, 0),
                    'active_percentage': round((status_dict.get(True, 0) / total_users * 100) if total_users else 0, 2)
                }
            }
            return APIResponse.success(data=payload, message='Estadísticas completas de usuarios')
        except Exception as e:
            logger.error('Error obteniendo estadísticas de usuarios: %s', e, exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)


def _parse_activity_datetime(value):
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


def _format_activity_item(item):
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


@users_ns.route('/<int:user_id>/activity')
class UserActivity(Resource):
    @users_ns.doc(
        'get_user_activity',
        description='Get paginated activity feed for a specific actor',
        security=['Bearer'],
        params={
            'page': 'Page number',
            'limit': 'Items per page',
            'per_page': 'Items per page (alias)',
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
    def get(self, user_id):
        page = request.args.get('page', default=1, type=int) or 1
        limit = request.args.get('limit', type=int) or request.args.get('per_page', type=int) or 50

        query = ActivityLog.query.filter(ActivityLog.actor_id == user_id)

        entity = request.args.get('entity')
        action = request.args.get('action')
        severity = request.args.get('severity')
        entity_id = request.args.get('entity_id', type=int)
        animal_id = request.args.get('animal_id', type=int)
        from_value = request.args.get('from')
        to_value = request.args.get('to')

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

        from_dt = _parse_activity_datetime(from_value)
        to_dt = _parse_activity_datetime(to_value)
        if from_dt:
            if from_dt.tzinfo is None:
                from_dt = from_dt.replace(tzinfo=timezone.utc)
            query = query.filter(ActivityLog.created_at >= from_dt)
        if to_dt:
            if to_dt.tzinfo is None:
                to_dt = to_dt.replace(tzinfo=timezone.utc)
            query = query.filter(ActivityLog.created_at <= to_dt)

        query = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        pagination = query.paginate(page=page, per_page=int(limit), error_out=False)
        items = [_format_activity_item(item) for item in pagination.items]

        return APIResponse.paginated_success(
            data=items,
            page=page,
            limit=int(limit),
            total_items=pagination.total,
            message='Actividad obtenida'
        )

@users_ns.route('/status')
class UserStatusStats(Resource):
    @users_ns.doc('get_user_status_stats', description='Resumen de usuarios por estado', security=['Bearer'])
    @jwt_required()
    def get(self):
        try:
            active_count = User.query.filter_by(status=True).count()
            inactive_count = User.query.filter_by(status=False).count()
            total = active_count + inactive_count
            return APIResponse.success(data={
                'active_users': active_count,
                'inactive_users': inactive_count,
                'total_users': total,
                'active_percentage': round((active_count / total * 100) if total else 0, 2)
            }, message='Estadísticas de estado de usuarios')
        except Exception as e:
            logger.error('Error obteniendo estadísticas de estado: %s', e, exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)

@users_ns.route('/roles')
class UserRolesStats(Resource):
    @users_ns.doc('get_user_roles_stats', description='Distribución de usuarios por roles', security=['Bearer'])
    @jwt_required()
    def get(self):
        try:
            role_counts = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
            total = sum(count for _, count in role_counts)
            roles_payload = {
                role.value: {
                    'count': count,
                    'percentage': round((count / total * 100) if total else 0, 2)
                } for role, count in role_counts
            }
            return APIResponse.success(data={
                'roles': roles_payload,
                'total_users': total
            }, message='Distribución por roles')
        except Exception as e:
            logger.error('Error obteniendo estadísticas de roles: %s', e, exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)

# Ruta pública opcional para crear usuarios iniciales cuando no existe autenticación todavía
@users_ns.route('/public', endpoint='users_public_create')
class UserPublicCreate(Resource):
    @users_ns.doc('public_create_user', description='Crear un usuario sin autenticacion (habilitado por defecto; se puede desactivar con PUBLIC_USER_CREATION_ENABLED=false).')
    def post(self):
        try:
            data = request.get_json() or {}
            missing = [f for f in ['identification','fullname','password','email','phone','role'] if f not in data]
            if missing:
                return APIResponse.validation_error({m: 'Requerido' for m in missing})
            # Forzar hashing de contraseña usando método del modelo
            password_raw = data.pop('password')
            password_confirmation = data.pop('password_confirmation', None)
            if password_confirmation is not None and password_confirmation != password_raw:
                return APIResponse.validation_error({'password_confirmation': 'No coincide'})
            user = User(**data)
            user.set_password(password_raw)
            db.session.add(user)
            db.session.flush()
            db.session.commit()
            db.session.refresh(user)
            # APIResponse.created(data, message=...)
            return APIResponse.created(user.to_namespace_dict(), message='Usuario creado exitosamente')
        except IntegrityError as ie:
            db.session.rollback()
            return APIResponse.conflict('Violación de unicidad', details={'error': str(ie)})
        except Exception as e:
            db.session.rollback()
            logger.error('Error en creación pública de usuario: %s', e, exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)
