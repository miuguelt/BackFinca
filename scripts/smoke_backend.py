import os
import sys
import time
import json
import traceback

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = os.environ.get('BASE_URL', 'https://localhost:8081/api/v1')
ADMIN_IDENT = os.environ.get('ADMIN_IDENT', '99999999')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'password123')

s = requests.Session()
s.verify = False
s.headers.update({'User-Agent': 'BackendSmoke/1.0', 'Accept': 'application/json'})

report = []
created_ids = {
    'disease': None,
}


def step(name):
    def deco(fn):
        def wrapper():
            start = time.time()
            try:
                out = fn()
                elapsed = (time.time() - start) * 1000
                report.append({'step': name, 'status': 'OK', 'ms': int(elapsed), 'detail': out})
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                tb = traceback.format_exc(limit=2)
                report.append({'step': name, 'status': 'FAIL', 'ms': int(elapsed), 'error': str(e), 'trace': tb})
        return wrapper
    return deco


@step('health')
def check_health():
    r = s.get(f"{BASE}/health", timeout=10)
    assert r.status_code == 200, f"health status {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data.get('status') in (True, 'ok', 'OK', 'healthy') or 'status' in data, data
    return {'status_code': r.status_code}


@step('swagger.json')
def check_swagger():
    r = s.get(f"{BASE}/swagger.json", timeout=20)
    assert r.status_code == 200, f"swagger status {r.status_code}"
    data = r.json()
    assert 'paths' in data and '/diseases/' in data['paths'] and '/fields/' in data['paths'], 'missing diseases/fields in swagger'
    return {'paths_count': len(data.get('paths', {}))}


@step('auth.login')
def login_admin():
    r = s.post(f"{BASE}/auth/login", json={'identification': ADMIN_IDENT, 'password': ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"login status {r.status_code}: {r.text[:200]}"
    # Expect JWT cookies to be set
    cookies = {c.name: c.value for c in s.cookies}
    assert any(k.lower().startswith('access') for k in cookies.keys()), f"no access cookie set: {cookies}"
    return {'cookies': list(cookies.keys())}


@step('animals.list')
def list_animals():
    r = s.get(f"{BASE}/animals/", params={'limit': 1}, timeout=20)
    assert r.status_code == 200, f"animals list status {r.status_code}: {r.text[:200]}"
    data = r.json()
    # Accept either array or object with items
    count = None
    if isinstance(data, list):
        count = len(data)
    elif isinstance(data, dict):
        count = len(data.get('items') or data.get('data') or [])
    return {'count': count}


@step('diseases.create')
def create_disease():
    payload = {
        'name': 'SDK Smoke Disease',
        'symptoms': 'none',
        'details': 'created by smoke_backend.py',
    }
    r = s.post(f"{BASE}/diseases/", json=payload, timeout=20)
    assert r.status_code in (200, 201), f"create disease status {r.status_code}: {r.text[:200]}"
    data = r.json()
    did = data.get('id') or data.get('data', {}).get('id')
    assert did, f"no id in response: {data}"
    created_ids['disease'] = did
    return {'id': did}


@step('diseases.get')
def get_disease():
    did = created_ids['disease']
    assert did, 'no disease created id'
    r = s.get(f"{BASE}/diseases/{did}", timeout=15)
    assert r.status_code == 200, f"get disease status {r.status_code}: {r.text[:200]}"
    data = r.json()
    name = data.get('name') or data.get('data', {}).get('name')
    assert name, 'missing name'
    return {'name': name}


@step('fields.stats')
def fields_stats():
    r = s.get(f"{BASE}/fields/stats", timeout=20)
    assert r.status_code == 200, f"fields stats status {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, (dict, list)), 'unexpected stats payload'
    return {'type': type(data).__name__}


@step('diseases.delete')
def delete_disease():
    did = created_ids['disease']
    assert did, 'no disease created id'
    r = s.delete(f"{BASE}/diseases/{did}", timeout=15)
    assert r.status_code in (200, 204), f"delete disease status {r.status_code}: {r.text[:200]}"
    return {'deleted_id': did}


def main():
    steps = [
        check_health,
        check_swagger,
        login_admin,
        list_animals,
        create_disease,
        get_disease,
        fields_stats,
        delete_disease,
    ]
    for fn in steps:
        fn()
    print(json.dumps({'ok': all(r['status']=='OK' for r in report), 'report': report}, ensure_ascii=False))


if __name__ == '__main__':
    main()