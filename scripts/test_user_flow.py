"""Standalone smoke script. Guarded to avoid interfering with pytest collection."""

import os
import requests

BASE = 'http://127.0.0.1:8081/api/v1'

def main():
    try:
        r = requests.get(BASE + '/swagger.json', timeout=3)
    except Exception as e:
        print('Server not running or not reachable:', e)
        return 1

    s = requests.Session()
    user_payload = {
        'identification': 12345678,
        'fullname': 'Test User',
        'password': 'pass1234',
        'email': 'test.user@example.com',
        'phone': '3001112222',
        'address': 'Test Street',
        'role': {'value': 'Aprendiz'},
        'status': True
    }
    print('Creating user...')
    r = s.post(BASE + '/users', json=user_payload)
    try:
        print('CREATE', r.status_code, r.json())
    except Exception:
        print('CREATE', r.status_code, r.text[:400])

    login_payload = {'identifier': 12345678, 'password': 'pass1234'}
    print('Logging in...')
    try:
        r = s.post(BASE + '/auth/login', json=login_payload)
        print('LOGIN', r.status_code, r.text[:400])
    except Exception as e:
        print('Login request failed:', e)
        return 1

    if r.status_code == 200:
        print('Access protected endpoint /users/statistics')
        r2 = s.get(BASE + '/users/statistics')
        print('STAT', r2.status_code, r2.text[:400])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
