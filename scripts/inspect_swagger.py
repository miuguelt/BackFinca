import requests, json
BASE='http://127.0.0.1:8081'
try:
    r = requests.get(BASE + '/api/v1/swagger.json', timeout=5)
    r.raise_for_status()
    spec = r.json()
    # Flask-RESTX may put models under 'definitions' or 'components' depending version
    defs = spec.get('definitions') or spec.get('components', {}).get('schemas') or {}
    for name in sorted(defs.keys()):
        if 'User' in name or name.lower().startswith('user'):
            print('\nMODEL:', name)
            print(json.dumps(defs[name], indent=2, ensure_ascii=False)[:2000])
except Exception as e:
    print('Error fetching swagger:', e)
