"""
Handlers y utilidades para JWT (flask_jwt_extended).
"""
from datetime import timezone, datetime
import logging
from flask import current_app


def configure_jwt_handlers(jwt):
    """Configura los handlers para errores de JWT usando APIResponse estándar."""
    from app.utils.response_handler import APIResponse
    logger = logging.getLogger(__name__)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        exp_timestamp = jwt_payload['exp']
        exp_utc = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        seconds_ago = int((now_utc - exp_utc).total_seconds())
        logger.warning(f"Expired token: expired {seconds_ago} seconds ago. Payload: {jwt_payload}")
        details = {
            'expired_at_utc': exp_utc.isoformat(),
            'current_time_utc': now_utc.isoformat(),
            'seconds_expired': seconds_ago
        }
        return APIResponse.error("Token expirado", status_code=401, error_code="TOKEN_EXPIRED", details=details)

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        logger.error(f"Invalid token: {error}")
        return APIResponse.error("Token inválido", status_code=401, error_code="INVALID_TOKEN", details={'error': str(error)})

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        logger.warning(f"Missing token: {error}")
        return APIResponse.error("Token ausente en la solicitud", status_code=401, error_code="MISSING_TOKEN", details={'error': str(error)})

    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        return {
            'server_time_utc': datetime.now(timezone.utc).isoformat(),
            'server_env': current_app.config.get('CONFIG_NAME')
        }