"""Utility to generate a secure JWT_SECRET_KEY and optionally write it to .env or .env.production

Usage:
  python tools/generate_jwt_secret.py --print
  python tools/generate_jwt_secret.py --write .env.production
"""
import secrets
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--print', action='store_true', help='Print the generated secret')
parser.add_argument('--write', type=str, help='Path to write the JWT_SECRET_KEY into (e.g. .env.production)')
args = parser.parse_args()

secret = secrets.token_hex(32)
if args.print:
    print(secret)
if args.write:
    p = Path(args.write)
    if not p.exists():
        print(f"File {p} does not exist. Will create and write JWT_SECRET_KEY entry.")
        p.write_text(f"JWT_SECRET_KEY={secret}\n", encoding='utf-8')
        print(f"Wrote JWT_SECRET_KEY to {p}")
    else:
        # Append or replace existing line
        txt = p.read_text(encoding='utf-8')
        if 'JWT_SECRET_KEY=' in txt:
            new_txt = []
            replaced = False
            for line in txt.splitlines():
                if line.startswith('JWT_SECRET_KEY='):
                    new_txt.append(f'JWT_SECRET_KEY={secret}')
                    replaced = True
                else:
                    new_txt.append(line)
            if not replaced:
                new_txt.append(f'JWT_SECRET_KEY={secret}')
            p.write_text('\n'.join(new_txt) + '\n', encoding='utf-8')
            print(f"Replaced JWT_SECRET_KEY in {p}")
        else:
            p.write_text(txt + '\n' + f'JWT_SECRET_KEY={secret}\n', encoding='utf-8')
            print(f"Appended JWT_SECRET_KEY to {p}")
