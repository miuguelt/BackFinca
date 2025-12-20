from flask_restx import Namespace, Resource, fields
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, set_access_cookies, 
    set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request,
    decode_token
)
from flask_jwt_extended.exceptions import CSRFError, JWTExtendedException
from app import db
from app.models.user import User
from app.utils.response_handler import APIResponse
from app.utils.security_logger import (
    log_authentication_attempt, 
    log_jwt_token_event,
    log_admin_action
)
from app.utils.token_blocklist import mark_token_revoked
from app.utils.validators import validate_password, ValidationError as ValidatorError
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

def _mask_email(email: str) -> str:
    """Return a masked version of the email for friendly responses."""
    try:
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + "*" * max(len(local) - 1, 1)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
    except Exception:
        return "***"


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
        change_limit = auth_limits.get('change_password', "10 per hour")
        recover_limit = auth_limits.get('recover', "5 per hour")
        reset_limit = auth_limits.get('reset', "5 per hour")

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
        
        
        # Aplicar limites a los metodos de los recursos
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
        try:
            ChangePasswordResource.post = limiter.limit(change_limit, key_func=get_user_id)(ChangePasswordResource.post)
            ChangePasswordResource.post._rate_limit_applied = True
        except Exception:
            logger.exception("No se pudo aplicar rate limit a ChangePasswordResource.post")
        try:
            PasswordRecoverResource.post = limiter.limit(recover_limit, key_func=get_remote_address_with_forwarded)(PasswordRecoverResource.post)
            PasswordRecoverResource.post._rate_limit_applied = True
        except Exception:
            logger.exception("No se pudo aplicar rate limit a PasswordRecoverResource.post")
        try:
            PasswordResetResource.post = limiter.limit(reset_limit, key_func=get_remote_address_with_forwarded)(PasswordResetResource.post)
            PasswordResetResource.post._rate_limit_applied = True
        except Exception:
            logger.exception("No se pudo aplicar rate limit a PasswordResetResource.post")
        # Aplicar exencion de rate limit para /auth/me (endpoint de verificacion frecuente)
        try:
            if not hasattr(CurrentUserResource.get, '_rate_limit_exempted'):
                CurrentUserResource.get = limiter.exempt(CurrentUserResource.get)
                CurrentUserResource.get._rate_limit_exempted = True
        except Exception:
            logger.exception("No se pudo configurar la exención de rate limit para CurrentUserResource.get")
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

password_change_model = auth_ns.model('PasswordChange', {
    'current_password': fields.String(required=True, description='Contrasena actual', example='OldPass123!'),
    'new_password': fields.String(required=True, description='Nueva contrasena (minimo 8 caracteres, compleja)', example='NewPass123!')
})

password_recover_model = auth_ns.model('PasswordRecoverRequest', {
    'identifier': fields.Raw(required=False, description='Email o numero de identificacion', example='user@example.com'),
    'email': fields.String(required=False, description='Alias: email del usuario', example='user@example.com'),
    'identification': fields.Raw(required=False, description='Alias: numero de identificacion', example='12345678')
})

password_reset_model = auth_ns.model('PasswordReset', {
    'reset_token': fields.String(required=True, description='Token de recuperacion generado en /auth/recover'),
    'new_password': fields.String(required=True, description='Nueva contrasena valida', example='NewPass123!')
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
    @staticmethod
    def _perform_refresh():
        """Lógica compartida para POST/GET con manejo explícito de errores JWT/CSRF."""
        try:
            verify_jwt_in_request(refresh=True)
            current_user_id = get_jwt_identity()
        except CSRFError as e:
            logger.warning('CSRF error during refresh: %s', e)
            return APIResponse.error(
                'CSRF token inválido o ausente',
                status_code=401,
                error_code='CSRF_ERROR',
                details={'error': str(e)}
            )
        except JWTExtendedException as e:
            logger.warning('JWT error during refresh: %s', e)
            return APIResponse.error(
                'Token faltante o inválido',
                status_code=401,
                error_code='JWT_ERROR',
                details={'error': str(e)}
            )
        except Exception as e:
            logger.error('Unexpected error validating refresh token: %s', e, exc_info=True)
            return APIResponse.error('Error al validar token', status_code=500, details={'error': str(e)})
        
        try:
            # Convertir a int si es posible (tokens usan identity string)
            try:
                user_id_int = int(current_user_id)
            except Exception:
                user_id_int = current_user_id
            user = User.get_by_id(user_id_int)
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
            return APIResponse.error('Error al renovar token', status_code=500, details={'error': str(e)})

    @auth_ns.doc('refresh_token')
    def post(self):
        """Renovar access token usando refresh token (POST)."""
        return self._perform_refresh()

    @auth_ns.doc('refresh_token_get')
    def get(self):
        """Renovar access token usando refresh token (GET para compatibilidad con clientes)."""
        return self._perform_refresh()

# --- Rutas de Autenticación ---

@auth_ns.route('/logout')
class LogoutResource(Resource):
    @auth_ns.doc('logout_user')
    @jwt_required()
    def post(self):
        """Cerrar sesión y limpiar cookies JWT."""
        try:
            current_user_id = get_jwt_identity()
            decoded_access = get_jwt()
            access_revoked = mark_token_revoked(decoded_access)
            refresh_revoked = False

            # Intentar revocar también el refresh token si viene en la cookie
            try:
                refresh_cookie_name = current_app.config.get('JWT_REFRESH_COOKIE_NAME', 'refresh_token_cookie')
                refresh_token = request.cookies.get(refresh_cookie_name)
                if refresh_token:
                    decoded_refresh = decode_token(refresh_token)
                    refresh_revoked = mark_token_revoked(decoded_refresh)
            except Exception as decode_err:
                logger.warning("No se pudo revocar el refresh token en logout: %s", decode_err)

            log_jwt_token_event('LOGOUT', current_user_id, {
                'token_revoked': access_revoked,
                'refresh_token_revoked': refresh_revoked
            })
            
            # Construir respuesta JSON y luego limpiar cookies sobre el objeto Response
            api_response_dict, status_code = APIResponse.success(
                message='Sesión cerrada exitosamente',
                data={'should_clear_auth': True}
            )
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

            # Envolver en clave 'user' para compatibilidad con el frontend
            return APIResponse.success(
                message='Usuario obtenido exitosamente',
                data={'user': user.to_namespace_dict()}
            )

        except Exception as e:
            logger.error(f"Error obteniendo usuario actual (ID: {get_jwt_identity()}): {e}", exc_info=True)
            return APIResponse.error('Error interno del servidor', details={'error': str(e)}, status_code=500)


@auth_ns.route('/change-password')
class ChangePasswordResource(Resource):
    @auth_ns.doc('change_password', description='Actualizar la contrasena del usuario autenticado.')
    @auth_ns.expect(password_change_model)
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return APIResponse.validation_error({
                'current_password': 'Requerido',
                'new_password': 'Requerido'
            })

        try:
            validate_password(new_password, field_name='new_password')
        except ValidatorError as ve:
            field = ve.field or 'new_password'
            return APIResponse.validation_error({field: ve.message})

        try:
            user_id = get_jwt_identity()
            try:
                user_id_int = int(user_id)
            except Exception:
                user_id_int = user_id

            user = User.get_by_id(user_id_int)
            if not user:
                return APIResponse.not_found('Usuario')
            if not user.status:
                return APIResponse.error('Usuario inactivo', status_code=403)
            if not user.check_password(current_password):
                return APIResponse.unauthorized('Contrasena actual incorrecta')
            if user.check_password(new_password):
                return APIResponse.validation_error({'new_password': 'La nueva contrasena no puede ser igual a la actual'})

            user.set_password(new_password)
            db.session.add(user)
            db.session.commit()

            # Revocar tokens actuales para forzar re-login
            try:
                decoded_access = get_jwt()
                mark_token_revoked(decoded_access)
                refresh_cookie_name = current_app.config.get('JWT_REFRESH_COOKIE_NAME', 'refresh_token_cookie')
                refresh_token = request.cookies.get(refresh_cookie_name)
                if refresh_token:
                    decoded_refresh = decode_token(refresh_token)
                    mark_token_revoked(decoded_refresh)
            except Exception as revoke_err:
                logger.debug("No se pudo revocar tokens en cambio de contrasena: %s", revoke_err)

            try:
                log_admin_action(user.id, 'PASSWORD_CHANGE', 'User', user.id, changes={'self_service': True})
            except Exception:
                logger.debug("No se pudo registrar log de cambio de contrasena", exc_info=True)

            return APIResponse.success(
                message='Contrasena actualizada correctamente',
                data={'should_clear_auth': True}
            )
        except Exception as e:
            logger.error(f'Error actualizando contrasena para usuario {get_jwt_identity()}: {e}', exc_info=True)
            db.session.rollback()
            return APIResponse.error('Error al actualizar contrasena', status_code=500, details={'error': str(e)})


@auth_ns.route('/recover')
class PasswordRecoverResource(Resource):
    @auth_ns.doc('recover_password', description='Generar token temporal para recuperar la contrasena por email o identificacion.')
    @auth_ns.expect(password_recover_model)
    def post(self):
        data = request.get_json() or {}
        identifier = data.get('identifier') or data.get('email') or data.get('identification')
        if isinstance(identifier, (int, float)):
            identifier = str(int(identifier))

        if not identifier:
            return APIResponse.validation_error({'identifier': 'Se requiere email o identificacion'})

        user = User.query.filter(
            (User.email == identifier) | (User.identification == identifier)
        ).first()

        if not user:
            return APIResponse.not_found('Usuario')
        if not user.status:
            return APIResponse.error('Usuario inactivo', status_code=403)

        # Calcular expiracion del token de recuperacion
        minutes_conf = current_app.config.get('PASSWORD_RESET_TOKEN_MINUTES', 15)
        try:
            minutes_conf = int(minutes_conf)
        except Exception:
            minutes_conf = 15
        expires_delta = timedelta(minutes=minutes_conf)

        reset_token = create_refresh_token(
            identity=str(user.id),
            additional_claims={'purpose': 'password_reset', 'email': user.email},
            expires_delta=expires_delta
        )

        try:
            log_admin_action(user.id, 'PASSWORD_RESET_REQUEST', 'User', user.id, changes={'via': 'recover_endpoint'})
        except Exception:
            logger.debug("No se pudo registrar log de solicitud de recuperacion", exc_info=True)

        return APIResponse.success(
            message='Token de recuperacion generado',
            data={
                'reset_token': reset_token,
                'expires_in': int(expires_delta.total_seconds()),
                'email_hint': _mask_email(user.email)
            }
        )


@auth_ns.route('/reset-password')
class PasswordResetResource(Resource):
    @auth_ns.doc('reset_password', description='Restablecer contrasena usando el token generado en /auth/recover.')
    @auth_ns.expect(password_reset_model)
    def post(self):
        data = request.get_json() or {}
        reset_token = data.get('reset_token')
        new_password = data.get('new_password')

        if not reset_token or not new_password:
            return APIResponse.validation_error({
                'reset_token': 'Requerido',
                'new_password': 'Requerido'
            })

        try:
            validate_password(new_password, field_name='new_password')
        except ValidatorError as ve:
            field = ve.field or 'new_password'
            return APIResponse.validation_error({field: ve.message})

        try:
            decoded = decode_token(reset_token)
        except JWTExtendedException as e:
            return APIResponse.unauthorized('Token de recuperacion invalido o expirado', details={'error': str(e)})
        except Exception as e:
            logger.error(f"Error decodificando token de recuperacion: {e}", exc_info=True)
            return APIResponse.error('Error al validar token de recuperacion', status_code=500, details={'error': str(e)})

        if decoded.get('type') != 'refresh' or decoded.get('purpose') != 'password_reset':
            return APIResponse.unauthorized('Token de recuperacion invalido', details={'reason': decoded.get('type')})

        user_id = decoded.get('sub')
        try:
            user_id_int = int(user_id)
        except Exception:
            user_id_int = user_id

        user = User.get_by_id(user_id_int)
        if not user:
            return APIResponse.not_found('Usuario')
        if not user.status:
            return APIResponse.error('Usuario inactivo', status_code=403)
        if user.check_password(new_password):
            return APIResponse.validation_error({'new_password': 'La nueva contrasena no puede ser igual a la actual'})

        try:
            user.set_password(new_password)
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error guardando nueva contrasena para usuario {user_id}: {e}', exc_info=True)
            return APIResponse.error('Error al guardar la nueva contrasena', status_code=500, details={'error': str(e)})

        try:
            mark_token_revoked(decoded)
        except Exception:
            logger.debug("No se pudo marcar token de recuperacion como usado", exc_info=True)

        try:
            log_admin_action(user.id, 'PASSWORD_RESET', 'User', user.id, changes={'via': 'recover_endpoint'})
        except Exception:
            logger.debug("No se pudo registrar log de reset de contrasena", exc_info=True)

        return APIResponse.success(
            message='Contrasena restablecida correctamente',
            data={'should_clear_auth': True}
        )