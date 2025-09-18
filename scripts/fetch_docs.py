import os
import requests

url = 'http://127.0.0.1:8081/api/v1/docs/'
try:
    r = requests.get(url, timeout=5)
    print('STATUS', r.status_code)
    print(r.text[:800])
except Exception as e:
    print('ERROR', e)
