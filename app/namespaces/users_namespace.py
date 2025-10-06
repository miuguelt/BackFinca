
from flask_restx import Resource, fields
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.user import User, Role
from app.utils.namespace_helpers import create_optimized_namespace
from app.utils.response_handler import APIResponse
from app import db
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)



users_ns = create_optimized_namespace(
    name='users',
    description='👥 Gestión Optimizada de Usuarios del Sistema',
    model_class=User,
    path='/users'
)

# El endpoint POST se crea automáticamente por create_optimized_namespace
# No requiere autenticación por defecto

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
    @users_ns.doc('public_create_user', description='Crear un usuario sin autenticación (solo permitido si no existen usuarios previos).')
    def post(self):
        try:
            existing_count = User.query.count()
            if existing_count > 0:
                return APIResponse.error('Creación pública deshabilitada: ya existen usuarios', status_code=403)
            data = request.get_json() or {}
            missing = [f for f in ['identification','fullname','password','email','phone','role'] if f not in data]
            if missing:
                return APIResponse.validation_error({m: 'Requerido' for m in missing})
            # Forzar hashing de contraseña usando método del modelo
            password_raw = data.pop('password')
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
            return APIResponse.error('Violación de unicidad', details={'error': str(ie)}, status_code=409)
        except Exception as e:
            db.session.rollback()
            logger.error('Error en creación pública de usuario: %s', e, exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)
