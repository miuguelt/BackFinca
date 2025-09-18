import os
import sys
import json
from pathlib import Path
from importlib import import_module

# Ensure project root is on sys.path so `import app` works when running this script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app

results = {}
for env in ('development', 'production'):
    try:
        app = create_app(env)
        cfg = app.config
        jwt_info = {
            'JWT_TOKEN_LOCATION': cfg.get('JWT_TOKEN_LOCATION'),
            'JWT_COOKIE_SECURE': cfg.get('JWT_COOKIE_SECURE'),
            'JWT_COOKIE_SAMESITE': cfg.get('JWT_COOKIE_SAMESITE'),
            'JWT_COOKIE_DOMAIN': cfg.get('JWT_COOKIE_DOMAIN'),
            'JWT_COOKIE_HTTPONLY': cfg.get('JWT_COOKIE_HTTPONLY'),
            'JWT_ACCESS_COOKIE_NAME': cfg.get('JWT_ACCESS_COOKIE_NAME'),
        }
        # Find auth-related routes
        auth_routes = [r.rule for r in app.url_map.iter_rules() if '/auth' in r.rule or r.rule.endswith('/login')]
        has_login = any('/auth/login' in r for r in auth_routes)

        # Check JWTManager registration
        jwt_registered = 'jwt' in app.extensions or 'flask_jwt_extended' in app.extensions

        # Use test client to call debug endpoint
        client = app.test_client()
        resp = client.get('/debug-complete')
        try:
            debug_json = resp.get_json()
        except Exception:
            debug_json = {'status_code': resp.status_code, 'text': resp.get_data(as_text=True)[:1000]}

        results[env] = {
            'config_jwt': jwt_info,
            'auth_routes_sample': auth_routes[:10],
            'has_auth_login_route': has_login,
            'jwt_registered_in_extensions': jwt_registered,
            'debug_complete_response': debug_json
        }
    except Exception as e:
        results[env] = {'error': str(e)}

print(json.dumps(results, indent=2, ensure_ascii=False))
