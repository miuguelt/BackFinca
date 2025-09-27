from flask_restx import Namespace, Resource, fields
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt, set_access_cookies, 
    set_refresh_cookies, unset_jwt_cookies
)
from app.models.user import User
from app.utils.response_handler import APIResponse
from app.utils.security_logger import (
    log_authentication_attempt, 
    log_jwt_token_event,
    log_admin_action
)
from datetime import timedelta
import logging

# Crear el namespace
auth_ns = Namespace(
    'auth',
    description='🔐 Autenticación y Autorización Optimizada',
    path='/auth'
)

logger = logging.getLogger(__name__)

# Importar limiter para aplicar rate limiting después de que la app esté inicializada
limiter = None


def set_limiter(app_limiter):
    """Configurar el limiter después de la inicialización de la app y aplicar límites por endpoint."""
    global limiter
    limiter = app_limiter
    try:
        if not limiter:
            return
        # Importar configuración de límites sin crear ciclos a nivel de módulo
        from app.utils.rate_limiter import RATE_LIMIT_CONFIG, get_user_id, get_remote_address_with_forwarded
        auth_limits = RATE_LIMIT_CONFIG.get('auth', {}) or {}
        login_limit = auth_limits.get('login', "5 per minute")
        refresh_limit = auth_limits.get('refresh', "10 per minute")
        logout_limit = auth_limits.get('logout', "20 per minute")

        # Key func específico para login: IP + identifier/identification/email
        def login_key_func():
            try:
                ip = get_remote_address_with_forwarded()
            except Exception:
                ip = (request.remote_addr or '127.0.0.1') if request else '127.0.0.1'
            ident = None
            try:
                data = request.get_json(silent=True) or {}
                ident = data.get('identifier') or data.get('identification') or data.get('email')
                if isinstance(ident, (int, float)):
                    ident = str(int(ident))
                if isinstance(ident, str):
                    ident = ident.strip().lower()
            except Exception:
                pass
            return f"{ip}|id:{ident or '-'}"
        
        # Evitar doble envoltura si ya se aplicó
        if hasattr(LoginResource.post, '_rate_limit_applied'):
            return
        
        # Aplicar límites a los métodos de los recursos
        try:
            LoginResource.post = limiter.limit(login_limit, key_func=login_key_func)(LoginResource.post)
            LoginResource.post._rate_limit_applied = True
        except Exception:
            logger.exception("No se pudo aplicar rate limit a LoginResource.post")
        try:
            RefreshTokenResource.post = limiter.limit(refresh_limit, key_func=get_user_id)(RefreshTokenResource.post)
            RefreshTokenResource.post._rate_limit_applied = True
        except Exception:
            logger.exception("No se pudo aplicar rate limit a RefreshTokenResource.post")
        try:
            LogoutResource.post = limiter.limit(logout_limit, key_func=get_user_id)(LogoutResource.post)
            LogoutResource.post._rate_limit_applied = True
        except Exception:
            logger.exception("No se pudo aplicar rate limit a LogoutResource.post")
    except Exception as e:
        logger.warning(f"No se pudo configurar/aplicar rate limiting en auth_namespace: {e}", exc_info=True)

# --- Modelos de Datos para Documentación ---
login_model = auth_ns.model('Login', {
    # Usar Raw para permitir número o string y evitar error de validación en Swagger UI
    'identifier': fields.Raw(required=False, description='Email o número de identificación (campo principal) (string | number)', example='12345678'),
    'identification': fields.Raw(required=False, description='Alias: número de identificación si no se envía identifier (string | number)', example='12345678'),
    'email': fields.String(required=False, description='Alias: email si no se envía identifier', example='user@example.com'),
    'password': fields.String(required=True, description='Contraseña', example='password123')
})

user_info_model = auth_ns.model('UserInfo', {
    'id': fields.Integer,
    'identification': fields.String,
    'fullname': fields.String,
    'email': fields.String,
    'role': fields.String,
    'status': fields.Boolean
})

login_response_model = auth_ns.model('LoginResponse', {
    'message': fields.String,
    'user': fields.Nested(user_info_model),
    'access_token': fields.String,
})

# --- Rutas de Autenticación ---

@auth_ns.route('/login')
class LoginResource(Resource):
    @auth_ns.doc('login_user', description='Autenticar usuario y generar tokens JWT. Acepta campos: identifier | identification | email')
    @auth_ns.expect(login_model)  # Validación manual para permitir alias
    def post(self):
        """Autenticar usuario y generar tokens JWT. Devuelve cookies HttpOnly y access_token en body."""
        data = request.get_json() or {}
        identifier = data.get('identifier') or data.get('identification') or data.get('email')
        # Convertir a string si viene numérico
        if isinstance(identifier, (int, float)):
            identifier = str(int(identifier))
        password = data.get('password')
        if not identifier or not password:
            return APIResponse.validation_error({
                'identifier': 'Se requiere uno de: identifier | identification | email',
                'password': 'Requerido'
            })
        try:
            # Eliminado: Bloque de debug que exponía información sensible en consola
            log_authentication_attempt(identifier, False)
            user = User.query.filter(
                (User.email == identifier) | (User.identification == identifier)
            ).first()
            if not user or not user.check_password(password):
                log_authentication_attempt(identifier, False, {'reason': 'invalid_credentials'})
                return APIResponse.error('Credenciales inválidas', status_code=401)
            if not user.status:
                log_authentication_attempt(identifier, False, {'reason': 'user_inactive'})
                return APIResponse.error('Usuario inactivo', status_code=403)
            user_claims = {
                'id': user.id,
                'identification': user.identification,
                'role': user.role.value,
                'fullname': user.fullname
            }
            # identity debe ser string para cumplir con PyJWT ("sub" string)
            identity = str(user.id)
            access_token = create_access_token(identity=identity, additional_claims=user_claims)
            refresh_token = create_refresh_token(identity=identity, additional_claims=user_claims)
            log_authentication_attempt(identifier, True, {'user_id': user.id, 'role': user.role.value})
            log_jwt_token_event('CREATED', user.id, {'access_token_created': True})

            # Respuesta optimizada y consistente
            user_dict = user.to_namespace_dict()
            expires_conf = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES')
            expires_in = int(expires_conf.total_seconds()) if isinstance(expires_conf, timedelta) else None

            response_data = {
                'user': user_dict,
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in
            }
            
            # Usar APIResponse para una estructura consistente
            # El método success devuelve una tupla (dict, status_code)
            api_response_dict, status_code = APIResponse.success(
                message='Login exitoso',
                data=response_data
            )

            # Crear la respuesta JSON y establecer las cookies
            resp = jsonify(api_response_dict)
            set_access_cookies(resp, access_token)
            set_refresh_cookies(resp, refresh_token)
            resp.status_code = status_code
            return resp
        except Exception as e:
            logger.error(f"Error en login para '{identifier}': {e}", exc_info=True)
            log_authentication_attempt(identifier, False, {'reason': 'server_error', 'error': str(e)})
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)

@auth_ns.route('/refresh')
class RefreshTokenResource(Resource):
    @auth_ns.doc('refresh_token')
    @jwt_required(refresh=True)
    def post(self):
        """Renovar access token usando refresh token."""
        try:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            if not user or not user.status:
                return APIResponse.error('Usuario inválido o inactivo', status_code=403)
            
            user_claims = {
                'id': user.id,
                'identification': user.identification,
                'role': user.role.value,
                'fullname': user.fullname
            }
            identity = str(user.id)
            new_access_token = create_access_token(identity=identity, additional_claims=user_claims)
            
            log_jwt_token_event('REFRESHED', user.id, {'new_access_token_created': True})
            
            response_data = {
                'access_token': new_access_token,
                'token_type': 'Bearer',
                'expires_in': int(current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1)).total_seconds())
            }
            
            api_response_dict, status_code = APIResponse.success(
                message='Token renovado exitosamente',
                data=response_data
            )
            
            resp = jsonify(api_response_dict)
            set_access_cookies(resp, new_access_token)
            resp.status_code = status_code
            return resp
        except Exception as e:
            logger.error(f'Error en refresh token: {e}', exc_info=True)
            return APIResponse.error('Error al renovar token', status_code=500)

# --- Rutas de Autenticación ---

@auth_ns.route('/logout')
class LogoutResource(Resource):
    @auth_ns.doc('logout_user')
    @jwt_required()
    def post(self):
        """Cerrar sesión y limpiar cookies JWT."""
        try:
            current_user_id = get_jwt_identity()
            log_jwt_token_event('LOGOUT', current_user_id)
            
            # Construir respuesta JSON y luego limpiar cookies sobre el objeto Response
            api_response_dict, status_code = APIResponse.success(message='Sesión cerrada exitosamente')
            resp = jsonify(api_response_dict)
            unset_jwt_cookies(resp)
            resp.status_code = status_code
            return resp
        except Exception as e:
            logger.error(f'Error en logout: {e}', exc_info=True)
            return APIResponse.error('Error al cerrar sesión', status_code=500)

@auth_ns.route('/me')
class CurrentUserResource(Resource):
    @auth_ns.doc('get_current_user', description='Obtener información del usuario autenticado.')
    @jwt_required()
    def get(self):
        """Obtener información del usuario actual"""
        try:
            user_id = get_jwt_identity()
            # Convertir a int si es posible (tokens usan identity string)
            try:
                user_id_int = int(user_id)
            except Exception:
                user_id_int = user_id
            user = User.get_by_id(user_id_int)

            if not user:
                return APIResponse.not_found('Usuario')
            if not user.status:
                return APIResponse.error('Usuario inactivo', status_code=403)

            return APIResponse.success(message='Usuario obtenido exitosamente', data=user.to_namespace_dict())

        except Exception as e:
            logger.error(f"Error obteniendo usuario actual (ID: {get_jwt_identity()}): {e}", exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)
