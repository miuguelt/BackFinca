"""User Preferences Namespace - Favorites and Settings"""
from flask_restx import Namespace, Resource, fields
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from typing import Optional
import logging
import threading
import time

from app import db, cache
from app.utils.response_handler import APIResponse

logger = logging.getLogger(__name__)

_fallback_cache = {}
_fallback_cache_lock = threading.Lock()
_redis_health = {"ok": True, "ts": 0.0}
_REDIS_HEALTH_TTL_SECONDS = 5.0


def _redis_cache_available() -> bool:
    try:
        if current_app.config.get('CACHE_TYPE') != 'redis':
            return True
    except Exception:
        return True
    now = time.time()
    if now - _redis_health["ts"] < _REDIS_HEALTH_TTL_SECONDS:
        return _redis_health["ok"]
    try:
        from app.utils.cache_utils import _get_redis_client
        ok = _get_redis_client() is not None
    except Exception:
        ok = False
    _redis_health["ok"] = ok
    _redis_health["ts"] = now
    return ok


def _fallback_get(key: str):
    with _fallback_cache_lock:
        entry = _fallback_cache.get(key)
    if not entry:
        return None
    value, expires_at = entry
    if expires_at and time.time() >= expires_at:
        with _fallback_cache_lock:
            _fallback_cache.pop(key, None)
        return None
    return value


def _fallback_set(key: str, value, timeout: Optional[int] = None) -> None:
    expires_at = None
    if timeout:
        expires_at = time.time() + int(timeout)
    with _fallback_cache_lock:
        _fallback_cache[key] = (value, expires_at)


def _fallback_delete(key: str) -> None:
    with _fallback_cache_lock:
        _fallback_cache.pop(key, None)


def _cache_get(key: str):
    if not _redis_cache_available():
        return _fallback_get(key)
    try:
        return cache.get(key)
    except Exception:
        return _fallback_get(key)


def _cache_set(key: str, value, timeout: Optional[int] = None) -> None:
    if not _redis_cache_available():
        _fallback_set(key, value, timeout)
        return
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        _fallback_set(key, value, timeout)


def _cache_delete(key: str) -> None:
    if not _redis_cache_available():
        _fallback_delete(key)
        return
    try:
        cache.delete(key)
    except Exception:
        _fallback_delete(key)

prefs_ns = Namespace(
    'preferences',
    description='👤 User Preferences - Favoritos y configuración personal',
    path='/preferences'
)

# Response models
favorite_model = prefs_ns.model('Favorite', {
    'id': fields.Integer(description='Favorite ID'),
    'endpoint': fields.String(required=True, description='Endpoint path'),
    'label': fields.String(description='Custom label'),
    'method': fields.String(description='HTTP method'),
    'created_at': fields.DateTime(description='Creation date')
})

favorites_list_model = prefs_ns.model('FavoritesList', {
    'favorites': fields.List(fields.Nested(favorite_model)),
    'count': fields.Integer(description='Total favorites')
})


@prefs_ns.route('/favorites')
class UserFavorites(Resource):
    """User's favorite endpoints"""

    @prefs_ns.doc(
        'get_favorites',
        description='Obtener lista de endpoints favoritos del usuario',
        security=['Bearer', 'Cookie']
    )
    @prefs_ns.marshal_with(favorites_list_model)
    @jwt_required()
    def get(self):
        """Get user's favorite endpoints"""
        try:
            user_id = get_jwt_identity()

            # Try to get from cache first
            cache_key = f"favorites_{user_id}"
            cached_favorites = _cache_get(cache_key)

            if cached_favorites:
                logger.debug(f"Cache hit for favorites user {user_id}")
                return APIResponse.success(data=cached_favorites)

            # Get from database (localStorage simulation using dict)
            # In production, this would query a favorites table
            favorites = get_user_favorites_from_storage(user_id)

            # Cache for 5 minutes
            _cache_set(cache_key, favorites, timeout=300)

            return APIResponse.success(
                data={
                    'favorites': favorites,
                    'count': len(favorites)
                },
                message='Favoritos cargados exitosamente'
            )

        except Exception as e:
            logger.error(f"Error getting favorites: {e}", exc_info=True)
            return APIResponse.error(
                message='Error al obtener favoritos',
                details=str(e),
                status_code=500
            )

    @prefs_ns.doc(
        'add_favorite',
        description='Agregar endpoint a favoritos',
        security=['Bearer', 'Cookie']
    )
    @prefs_ns.expect(favorite_model)
    @jwt_required()
    def post(self):
        """Add endpoint to favorites"""
        try:
            user_id = get_jwt_identity()
            data = request.json

            # Validate required fields
            if not data.get('endpoint'):
                return APIResponse.error(
                    message='El campo endpoint es requerido',
                    status_code=400
                )

            # Create favorite entry
            favorite = {
                'endpoint': data['endpoint'],
                'label': data.get('label', data['endpoint']),
                'method': data.get('method', 'GET'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            # Save to storage
            save_user_favorite(user_id, favorite)

            # Invalidate cache
            _cache_delete(f"favorites_{user_id}")

            return APIResponse.success(
                data=favorite,
                message='Agregado a favoritos exitosamente',
                status_code=201
            )

        except Exception as e:
            logger.error(f"Error adding favorite: {e}", exc_info=True)
            return APIResponse.error(
                message='Error al agregar favorito',
                details=str(e),
                status_code=500
            )

    @prefs_ns.doc(
        'clear_favorites',
        description='Eliminar todos los favoritos',
        security=['Bearer', 'Cookie']
    )
    @jwt_required()
    def delete(self):
        """Clear all favorites"""
        try:
            user_id = get_jwt_identity()

            # Clear from storage
            clear_user_favorites(user_id)

            # Invalidate cache
            _cache_delete(f"favorites_{user_id}")

            return APIResponse.success(
                message='Favoritos eliminados exitosamente'
            )

        except Exception as e:
            logger.error(f"Error clearing favorites: {e}", exc_info=True)
            return APIResponse.error(
                message='Error al eliminar favoritos',
                details=str(e),
                status_code=500
            )


@prefs_ns.route('/favorites/<int:favorite_id>')
class UserFavorite(Resource):
    """Individual favorite endpoint"""

    @prefs_ns.doc(
        'delete_favorite',
        description='Eliminar un favorito específico',
        security=['Bearer', 'Cookie']
    )
    @jwt_required()
    def delete(self, favorite_id):
        """Delete specific favorite"""
        try:
            user_id = get_jwt_identity()

            # Remove from storage
            remove_user_favorite(user_id, favorite_id)

            # Invalidate cache
            _cache_delete(f"favorites_{user_id}")

            return APIResponse.success(
                message='Favorito eliminado exitosamente'
            )

        except Exception as e:
            logger.error(f"Error deleting favorite: {e}", exc_info=True)
            return APIResponse.error(
                message='Error al eliminar favorito',
                details=str(e),
                status_code=500
            )


@prefs_ns.route('/history')
class EndpointHistory(Resource):
    """User's endpoint usage history"""

    @prefs_ns.doc(
        'get_history',
        description='Obtener historial de endpoints usados recientemente',
        security=['Bearer', 'Cookie'],
        params={'limit': 'Number of recent endpoints (default: 10)'}
    )
    @jwt_required()
    def get(self):
        """Get recent endpoint usage history"""
        try:
            user_id = get_jwt_identity()
            limit = request.args.get('limit', 10, type=int)

            # Get from cache
            cache_key = f"history_{user_id}"
            history = _cache_get(cache_key) or []

            return APIResponse.success(
                data={
                    'history': history[:limit],
                    'count': len(history)
                }
            )

        except Exception as e:
            logger.error(f"Error getting history: {e}", exc_info=True)
            return APIResponse.error(
                message='Error al obtener historial',
                details=str(e),
                status_code=500
            )

    @prefs_ns.doc(
        'add_to_history',
        description='Agregar endpoint al historial',
        security=['Bearer', 'Cookie']
    )
    @jwt_required()
    def post(self):
        """Add endpoint to history"""
        try:
            user_id = get_jwt_identity()
            data = request.json

            if not data.get('endpoint'):
                return APIResponse.error(
                    message='El campo endpoint es requerido',
                    status_code=400
                )

            # Get current history
            cache_key = f"history_{user_id}"
            history = _cache_get(cache_key) or []

            # Add new entry
            new_entry = {
                'endpoint': data['endpoint'],
                'method': data.get('method', 'GET'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Remove duplicates and add to front
            history = [h for h in history if h['endpoint'] != data['endpoint']]
            history.insert(0, new_entry)

            # Keep only last 20
            history = history[:20]

            # Cache for 1 hour
            _cache_set(cache_key, history, timeout=3600)

            return APIResponse.success(
                message='Agregado al historial'
            )

        except Exception as e:
            logger.error(f"Error adding to history: {e}", exc_info=True)
            return APIResponse.error(
                message='Error al agregar al historial',
                details=str(e),
                status_code=500
            )


# ================================================================
# Helper functions for favorites storage
# In production, these would interact with a database table
# For now, using cache as temporary storage
# ================================================================

def get_user_favorites_from_storage(user_id):
    """Get user favorites from cache/storage"""
    cache_key = f"favorites_storage_{user_id}"
    favorites = _cache_get(cache_key) or []
    return favorites


def save_user_favorite(user_id, favorite):
    """Save favorite to storage"""
    cache_key = f"favorites_storage_{user_id}"
    favorites = _cache_get(cache_key) or []

    # Check if already exists
    for fav in favorites:
        if fav['endpoint'] == favorite['endpoint']:
            return  # Already exists

    # Add ID
    favorite['id'] = len(favorites) + 1
    favorites.append(favorite)

    # Save back to cache (24 hours)
    _cache_set(cache_key, favorites, timeout=86400)


def remove_user_favorite(user_id, favorite_id):
    """Remove specific favorite"""
    cache_key = f"favorites_storage_{user_id}"
    favorites = _cache_get(cache_key) or []

    # Filter out the favorite
    favorites = [f for f in favorites if f.get('id') != favorite_id]

    # Save back
    _cache_set(cache_key, favorites, timeout=86400)


def clear_user_favorites(user_id):
    """Clear all favorites"""
    cache_key = f"favorites_storage_{user_id}"
    _cache_delete(cache_key)
