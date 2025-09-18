"""Normalize inline response tuples in namespaces.

Replaces patterns like:
    200: ('Description', { ... }),
with:
    200: 'Description',

This avoids unregistered inline models breaking Flask-RESTX swagger generation.

This script edits files in-place under app/namespaces.
"""
import re
from pathlib import Path

ns_dir = Path(__file__).resolve().parents[1] / 'app' / 'namespaces'
pattern_single = re.compile(r"(200\s*:\s*\(\s*'([^']+)'\s*,\s*\{)", re.M)
pattern_double = re.compile(r'(200\s*:\s*\(\s*"([^"]+)"\s*,\s*\{)', re.M)

edited = []
for p in ns_dir.glob('*.py'):
    text = p.read_text(encoding='utf-8')
    new_text = text
    # handle single-quoted desc
    new_text, n1 = pattern_single.subn(lambda m: f"200: '{m.group(2)}',", new_text)
    new_text, n2 = pattern_double.subn(lambda m: f'200: "{m.group(2)}",', new_text)
    if (n1 + n2) > 0 and new_text != text:
        p.write_text(new_text, encoding='utf-8')
        edited.append((str(p), n1 + n2))

if not edited:
    print('No inline response tuples found.')
else:
    for f, count in edited:
        print(f'Edited {f}: replaced {count} inline 200 responses')
