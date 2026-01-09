import functools
import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable, Optional, Tuple

from flask import current_app, request

logger = logging.getLogger(__name__)

_local_locks: dict[str, threading.Lock] = {}
_local_locks_guard = threading.Lock()
_redis_health = {"ok": True, "ts": 0.0}
_REDIS_HEALTH_TTL_SECONDS = 5.0


def _get_cache():
    try:
        from app import cache as app_cache
        return app_cache
    except Exception:
        pass
    try:
        if current_app and current_app.extensions:
            return current_app.extensions.get("cache")
    except Exception:
        pass
    return None


def _get_redis_client():
    try:
        from redis import Redis
        url = None
        if current_app:
            url = current_app.config.get("CACHE_REDIS_URL") or current_app.config.get("REDIS_URL")
        if not url:
            return None
        client = Redis.from_url(url)
        client.ping()
        return client
    except Exception:
        return None


def _redis_cache_available() -> bool:
    try:
        if current_app and current_app.config.get("CACHE_TYPE") != "redis":
            return True
    except Exception:
        return True
    try:
        url = None
        if current_app:
            url = current_app.config.get("CACHE_REDIS_URL") or current_app.config.get("REDIS_URL")
        if not url:
            return False
    except Exception:
        pass
    now = time.time()
    if now - _redis_health["ts"] < _REDIS_HEALTH_TTL_SECONDS:
        return _redis_health["ok"]
    ok = _get_redis_client() is not None
    _redis_health["ok"] = ok
    _redis_health["ts"] = now
    return ok


def _is_redis_error(exc: Exception) -> bool:
    try:
        from redis.exceptions import RedisError
        if isinstance(exc, RedisError):
            return True
    except Exception:
        pass
    cur = exc
    seen = set()
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        mod = (type(cur).__module__ or "").lower()
        name = (type(cur).__name__ or "").lower()
        if "redis" in mod or "redis" in name:
            return True
        cur = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
    return False


def safe_cached(*cache_args, **cache_kwargs):
    def decorator(func):
        try:
            from app import cache as app_cache
        except Exception:
            app_cache = None

        if not app_cache:
            return func

        cached_func = app_cache.cached(*cache_args, **cache_kwargs)(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not _redis_cache_available():
                return func(*args, **kwargs)
            try:
                return cached_func(*args, **kwargs)
            except Exception as exc:
                if _is_redis_error(exc):
                    logger.warning("Redis cache error; bypassing cache", exc_info=True)
                    return func(*args, **kwargs)
                raise

        return wrapper

    return decorator


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_cache_key(prefix: str, parts: Any) -> str:
    return f"{prefix}:{stable_hash(parts)}"


def _acquire_local_lock(lock_key: str) -> threading.Lock:
    with _local_locks_guard:
        lock = _local_locks.get(lock_key)
        if lock is None:
            lock = threading.Lock()
            _local_locks[lock_key] = lock
        return lock


def singleflight(
    key: str,
    *,
    lock_ttl_seconds: int = 5,
    wait_seconds: float = 1.0,
) -> Tuple[bool, Optional[Callable[[], None]]]:
    """
    Best-effort "single flight" to avoid thundering herd.
    Returns (acquired, release_fn).
    """
    lock_key = f"sf:{key}"
    redis_client = _get_redis_client()
    if redis_client:
        try:
            acquired = bool(redis_client.set(lock_key, "1", nx=True, ex=lock_ttl_seconds))
            if acquired:
                return True, lambda: redis_client.delete(lock_key)
        except Exception:
            logger.debug("Single-flight redis lock fallo", exc_info=True)

        # Wait for someone else to compute and populate cache
        cache = _get_cache()
        if cache:
            deadline = time.time() + max(wait_seconds, 0.0)
            while time.time() < deadline:
                if cache.get(key) is not None:
                    return False, None
                time.sleep(0.05)
        return False, None

    # Local (single-process) lock
    lock = _acquire_local_lock(lock_key)
    acquired = lock.acquire(timeout=max(wait_seconds, 0.0))
    if acquired:
        return True, lock.release
    return False, None


def cached_json_with_etag(
    *,
    cache_key: str,
    ttl_seconds: int,
    compute: Callable[[], dict],
    private: bool = True,
) -> Tuple[dict, int, dict]:
    """
    Cache a JSON-serializable dict; stores {etag, payload}.
    Returns (payload, status_code, headers).
    """
    cache = _get_cache()
    if not cache:
        payload = compute()
        etag = f"\"{stable_hash(payload)[:24]}\""
        if_none_match = request.headers.get("If-None-Match") if request else None
        headers = {"ETag": etag, "Cache-Control": _cache_control(ttl_seconds, private=private)}
        headers["Vary"] = "Authorization, Cookie" if private else "Accept-Encoding"
        if if_none_match and etag and etag in [t.strip() for t in if_none_match.split(",")]:
            return {}, 304, headers
        return payload, 200, headers

    cached = None
    try:
        cached = cache.get(cache_key)
    except Exception:
        logger.debug("Cache get fallo key=%s", cache_key, exc_info=True)

    if isinstance(cached, dict) and "etag" in cached and "payload" in cached:
        etag = str(cached.get("etag") or "")
        if_none_match = request.headers.get("If-None-Match") if request else None
        if if_none_match and etag and etag in [t.strip() for t in if_none_match.split(",")]:
            headers = {"ETag": etag}
            headers["Cache-Control"] = _cache_control(ttl_seconds, private=private)
            headers["Vary"] = "Authorization, Cookie" if private else "Accept-Encoding"
            return {}, 304, headers
        headers = {"ETag": etag}
        headers["Cache-Control"] = _cache_control(ttl_seconds, private=private)
        headers["Vary"] = "Authorization, Cookie" if private else "Accept-Encoding"
        headers["X-Cache"] = "HIT"
        return cached["payload"], 200, headers

    acquired, release = singleflight(cache_key, lock_ttl_seconds=min(max(ttl_seconds, 5), 30))
    try:
        if not acquired:
            # Another worker may have computed. Retry one read.
            try:
                cached_retry = cache.get(cache_key)
                if isinstance(cached_retry, dict) and "etag" in cached_retry and "payload" in cached_retry:
                    etag = str(cached_retry.get("etag") or "")
                    headers = {"ETag": etag, "Cache-Control": _cache_control(ttl_seconds, private=private)}
                    headers["Vary"] = "Authorization, Cookie" if private else "Accept-Encoding"
                    headers["X-Cache"] = "HIT"
                    return cached_retry["payload"], 200, headers
            except Exception:
                pass

        payload = compute()
        etag = f"\"{stable_hash(payload)[:24]}\""
        try:
            cache.set(cache_key, {"etag": etag, "payload": payload}, timeout=ttl_seconds)
        except Exception:
            logger.debug("Cache set fallo key=%s", cache_key, exc_info=True)
        headers = {"ETag": etag, "Cache-Control": _cache_control(ttl_seconds, private=private)}
        headers["Vary"] = "Authorization, Cookie" if private else "Accept-Encoding"
        headers["X-Cache"] = "MISS"
        return payload, 200, headers
    finally:
        if release:
            try:
                release()
            except Exception:
                pass


def _cache_control(ttl_seconds: int, *, private: bool) -> str:
    ttl_seconds = max(int(ttl_seconds), 0)
    scope = "private" if private else "public"
    # small SW-friendly strategy; real SW can still do stale-while-revalidate
    return f"{scope}, max-age={ttl_seconds}"
