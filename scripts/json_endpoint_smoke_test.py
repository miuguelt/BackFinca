import json
import re
from typing import List, Dict, Any
from datetime import datetime
from time import perf_counter

from app import create_app
from flask import url_for

# Configuración
LOGIN_IDENTIFIER = 99999999
LOGIN_PASSWORD = 'password123'

# Paths públicos extraídos de enforce_jwt_protection (normalizados sin barra final)
PUBLIC_PATHS = {
    '/login','/logout','/refresh','/api-documentation','/docs','/docs/interactive','/docs/tester',
    '/api/v1/docs','/api/v1/docs/schema','/swaggerui','/swagger.json','/api/v1/swagger.json',
    '/metrics','/health','/api/v1/health','/api/v1/analytics/dashboard','/api/v1/analytics/alerts',
    '/api/v1/auth/login','/api/v1/login','/api/v1/users','/api/v1/users/public','/','/favicon.ico'
}

# Endpoints críticos para medir latencia con paginación estándar
CRITICAL_ENDPOINTS = [
    '/api/v1/animals',
    '/api/v1/users',
    '/api/v1/medications',
    '/api/v1/vaccines',
    '/api/v1/species',
    '/api/v1/fields'
]

# Campos que indican éxito esperado en respuestas estándar
SUCCESS_KEYS = {'success', 'message', 'data'}


def normalize_path(p: str) -> str:
    if not p:
        return '/'
    if p != '/' and p.endswith('/'):
        p = p[:-1]
    return p


def is_public(path: str) -> bool:
    np = normalize_path(path)
    return np in {normalize_path(x) for x in PUBLIC_PATHS}


def main():
    app = create_app('development')  # Usar entorno de desarrollo para aprovechar datos existentes
    client = app.test_client()

    results: List[Dict[str, Any]] = []
    auth_header = None

    # 1. Login para obtener token
    login_resp = client.post('/api/v1/auth/login', json={'identifier': LOGIN_IDENTIFIER, 'password': LOGIN_PASSWORD})
    login_json = None
    try:
        login_json = login_resp.get_json(silent=True)
    except Exception:
        pass
    if login_resp.status_code == 200 and login_json and login_json.get('data', {}).get('access_token'):
        token = login_json['data']['access_token']
        auth_header = {'Authorization': f'Bearer {token}'}
        results.append({'endpoint': '/api/v1/auth/login', 'method': 'POST', 'status': login_resp.status_code, 'ok': True, 'detail': 'Login exitoso'})
    else:
        results.append({'endpoint': '/api/v1/auth/login', 'method': 'POST', 'status': login_resp.status_code, 'ok': False, 'detail': 'Fallo login, abortando pruebas protegidas'})

    # 2. Recolectar rutas GET sin parámetros
    pattern_param = re.compile(r'<.*?>')
    tested_paths = set()

    with app.app_context():
        for rule in app.url_map.iter_rules():
            methods = rule.methods or set()
            if 'GET' not in methods:
                continue
            path = str(rule)
            if pattern_param.search(path):
                continue  # Omitir rutas con parámetros dinámicos
            if path.startswith('/static'):
                continue
            if path in tested_paths:
                continue
            tested_paths.add(path)

            headers = {}
            if not is_public(path) and auth_header:
                headers.update(auth_header)

            t0 = perf_counter()
            resp = client.get(path, headers=headers)
            latency_ms = (perf_counter() - t0) * 1000
            content_type = resp.headers.get('Content-Type','')
            is_json = 'application/json' in content_type.lower() or resp.data[:1] in (b'{', b'[')
            parsed = None
            parse_error = None
            if is_json:
                try:
                    parsed = resp.get_json(silent=True)
                except Exception as e:
                    parse_error = str(e)
            ok = resp.status_code in (200, 201, 202, 204, 302) and (parsed is not None or resp.status_code in (204, 302))
            results.append({
                'endpoint': path,
                'method': 'GET',
                'status': resp.status_code,
                'content_type': content_type,
                'json_valid': parsed is not None,
                'ok': ok,
                'error': parse_error,
                'latency_ms': round(latency_ms, 2),
                'has_success_schema': bool(parsed and isinstance(parsed, dict) and SUCCESS_KEYS.issubset(parsed.keys()))
            })

    # 2b. Medición de latencia en endpoints críticos con paginación (page=1, limit=50)
    if auth_header:
        for ep in CRITICAL_ENDPOINTS:
            headers = {} if is_public(ep) else dict(auth_header)
            samples = []
            statuses = []
            for _ in range(3):
                t0 = perf_counter()
                resp = client.get(f"{ep}?page=1&limit=50", headers=headers)
                samples.append((perf_counter() - t0) * 1000)
                statuses.append(resp.status_code)
            results.append({
                'endpoint': ep,
                'method': 'GET',
                'scenario': 'latency(page=1,limit=50)',
                'status_samples': statuses,
                'latency_avg_ms': round(sum(samples)/len(samples), 2),
                'latency_min_ms': round(min(samples), 2),
                'latency_max_ms': round(max(samples), 2)
            })

    # 3. Intentar obtener ejemplos de creación y probar POST (solo algunos)
    if auth_header:
        examples_resp = client.get('/api/v1/docs/examples', headers=auth_header)
        examples_json = examples_resp.get_json(silent=True)
        if examples_json and examples_json.get('data', {}).get('examples'):
            for ex in examples_json['data']['examples'][:5]:  # Limitar a 5 para no llenar la BD
                endpoint = ex.get('create_endpoint')
                payload = ex.get('create_request')
                if not endpoint or not payload:
                    continue
                # Evitar crear usuarios duplicados
                if 'user' in endpoint:
                    continue
                post_headers = {}
                if not is_public(endpoint) and auth_header:
                    post_headers.update(auth_header)
                t0 = perf_counter()
                post_resp = client.post(endpoint, json=payload, headers=post_headers)
                post_latency_ms = (perf_counter() - t0) * 1000
                post_ok_json = post_resp.get_json(silent=True)
                results.append({
                    'endpoint': endpoint,
                    'method': 'POST',
                    'status': post_resp.status_code,
                    'ok': post_resp.status_code in (200, 201),
                    'json_valid': post_ok_json is not None,
                    'latency_ms': round(post_latency_ms, 2)
                })

    # 4. Resumen
    total = len(results)
    passed = sum(1 for r in results if r.get('ok'))
    failed = total - passed

    summary = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'total_tests': total,
        'passed': passed,
        'failed': failed,
        'pass_rate_percent': round(passed * 100 / total, 2) if total else 0.0
    }

    output = {'summary': summary, 'results': results}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
