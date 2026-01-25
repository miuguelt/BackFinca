"""
Handlers y utilidades para JWT (flask_jwt_extended).
"""
from datetime import timezone, datetime
import logging
from flask import current_app, jsonify
from flask_jwt_extended import unset_jwt_cookies, unset_access_cookies

from app.utils.token_blocklist import is_token_revoked


def configure_jwt_handlers(jwt):
    """Configura los handlers para errores de JWT usando APIResponse estándar."""
    from app.utils.response_handler import APIResponse
    logger = logging.getLogger(__name__)
    def _clear_jwt_cookies(resp, token_type):
        if token_type == 'refresh':
            unset_jwt_cookies(resp)
        else:
            unset_access_cookies(resp)


    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        exp_timestamp = jwt_payload['exp']
        exp_utc = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        seconds_ago = int((now_utc - exp_utc).total_seconds())
        # Comentado: Evitar exponer payload del token en logs
        # logger.warning(f"Expired token: expired {seconds_ago} seconds ago. Payload: {jwt_payload}")
        logger.warning(f"Expired token: expired {seconds_ago} seconds ago")
        token_type = jwt_payload.get('type', 'access')
        
        # Determine client action based on token type
        if token_type == 'access':
            client_action = 'ATTEMPT_REFRESH'
            should_clear = False
        else:
            client_action = 'CLEAR_AUTH_AND_RELOGIN'
            should_clear = True

        details = {
            'expired_at_utc': exp_utc.isoformat(),
            'current_time_utc': now_utc.isoformat(),
            'seconds_expired': seconds_ago,
            'token_type': token_type,
            'client_action': client_action,
            'should_clear_auth': should_clear,
            'logout_url': '/api/v1/auth/logout'
        }
        if token_type == 'access':
            details['refresh_url'] = '/api/v1/auth/refresh'
        payload, status_code = APIResponse.error(
            "Token expirado",
            status_code=401,
            error_code="TOKEN_EXPIRED",
            details=details,
        )
        resp = jsonify(payload)
        _clear_jwt_cookies(resp, jwt_payload.get('type'))
        resp.status_code = status_code
        resp.headers['Cache-Control'] = 'no-store'
        return resp

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        logger.error(f"Invalid token: {error}")
        return APIResponse.error("Token inválido", status_code=401, error_code="INVALID_TOKEN", details={'error': str(error)})

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        reason = str(error or "")
        if "CSRF" in reason.upper():
            logger.warning(f"CSRF error: {reason}")
            return APIResponse.error(
                "CSRF token inválido o ausente",
                status_code=401,
                error_code="CSRF_ERROR",
                details={"reason": reason}
            )
        else:
            logger.warning(f"Unauthorized: {reason}")
            return APIResponse.error(
                "Token ausente o no autorizado",
                status_code=401,
                error_code="MISSING_TOKEN",
                details={"error": reason}
            )

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        try:
            revoked = is_token_revoked(jwt_payload)
            if revoked:
                logger.info("Token revocado detectado (sub=%s, type=%s)", jwt_payload.get('sub'), jwt_payload.get('type'))
            return revoked
        except Exception as e:
            logger.exception("Fallo verificando token en blocklist: %s", e)
            return False

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        logger.warning("Intento de uso de token revocado (sub=%s, type=%s)", jwt_payload.get('sub'), jwt_payload.get('type'))
        details = {
            'token_type': jwt_payload.get('type'),
            'client_action': 'CLEAR_AUTH_AND_RELOGIN',
            'should_clear_auth': True,
            'logout_url': '/api/v1/auth/logout'
        }
        payload, status_code = APIResponse.error(
            "Token revocado",
            status_code=401,
            error_code="TOKEN_REVOKED",
            details=details
        )
        resp = jsonify(payload)
        _clear_jwt_cookies(resp, jwt_payload.get('type'))
        resp.status_code = status_code
        resp.headers['Cache-Control'] = 'no-store'
        return resp

    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        return {
            'server_time_utc': datetime.now(timezone.utc).isoformat(),
            'server_env': current_app.config.get('CONFIG_NAME')
        }
