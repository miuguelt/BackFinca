import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = os.environ.get("API_BASE", "https://localhost:8081")
PATH_SUFFIX = os.environ.get("TEST_PATH", "/api/v1/treatments")
CREDS = {
    "identification": os.environ.get("TEST_IDENTIFICATION", "99999999"),
    "password": os.environ.get("TEST_PASSWORD", "password123"),
}

s = requests.Session()
s.verify = False

def print_cookie_jar(sess: requests.Session):
    if not sess.cookies:
        print("[cookies] (empty)")
        return
    print("[cookies] jar:")
    for c in sess.cookies:
        v = (c.value[:18] + "...") if len(c.value) > 18 else c.value
        print(f" - {c.name}={v}; domain={c.domain}; path={c.path}; secure={c.secure}; httponly=?")

print("BASE:", BASE)

print("\n--- LOGIN /auth/login ---")
try:
    r = s.post(f"{BASE}/api/v1/auth/login", json=CREDS, timeout=20)
    print("status:", r.status_code)
    print("Set-Cookie (login):", (r.headers.get("Set-Cookie", "") or "")[:600])
    try:
        j = r.json()
    except Exception:
        j = {}
    at = j.get("access_token")
    print("has access_token:", bool(at), "len:", len(at or ""))
    print_cookie_jar(s)
except Exception as e:
    print("LOGIN ERROR:", e)

print(f"\n--- GET {PATH_SUFFIX} (using cookies) ---")
try:
    r2 = s.get(f"{BASE}{PATH_SUFFIX}", timeout=20)
    print("status:", r2.status_code)
    cookie_hdr = r2.request.headers.get("Cookie", "")
    print("Cookie header sent:", cookie_hdr[:600])
    print("Set-Cookie (treatments):", (r2.headers.get("Set-Cookie", "") or "")[:600])
    txt = r2.text
    print("body:", txt[:800])

    # Bearer variant using access_token from body (if available)
    token = None
    try:
        j2 = r2.json()
        token = j2.get("access_token")
    except Exception:
        token = None
    if token:
        print(f"\n--- GET {PATH_SUFFIX} (using Authorization: Bearer) ---")
        try:
            r3 = requests.get(
                f"{BASE}{PATH_SUFFIX}",
                headers={"Authorization": f"Bearer {token}"},
                verify=False,
                timeout=20,
            )
            print("status:", r3.status_code)
            auth_hdr = r3.request.headers.get("Authorization", "")
            print("Authorization header sent:", auth_hdr[:120])
            print("body:", (r3.text or "")[:800])
        except Exception as e:
            print("TREATMENTS BEARER ERROR:", e)
    else:
        print("[warn] No access_token in response body; skipping Bearer test.")
except Exception as e:
    print("TREATMENTS ERROR:", e)