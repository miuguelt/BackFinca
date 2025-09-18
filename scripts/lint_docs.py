"""Simple Markdown docs linter.

Checks:
 - Heading blank lines
 - Fenced code blocks have language
 - No trailing whitespace
 - Max line length soft warning (120)

Usage: python scripts/lint_docs.py
"""
from pathlib import Path
import re
import sys

RE_FENCE = re.compile(r"^```(.*)")

def lint_file(path: Path):
    errors = []
    lines = path.read_text(encoding='utf-8').splitlines()
    inside_fence = False
    fence_lang_missing = False
    for i, line in enumerate(lines):
        ln = i + 1
        # trailing spaces
        if line.rstrip() != line:
            errors.append(f"{path}:{ln}: trailing whitespace")
        # headings blank line before (skip first line)
        if line.startswith('#'):
            if ln > 1 and lines[i-1].strip() != '':
                errors.append(f"{path}:{ln}: heading not preceded by blank line")
        m = RE_FENCE.match(line)
        if m:
            if not inside_fence:
                lang = m.group(1).strip()
                if not lang:
                    fence_lang_missing = True
                    errors.append(f"{path}:{ln}: fenced code block missing language")
                inside_fence = True
            else:
                inside_fence = False
        if len(line) > 120:
            errors.append(f"{path}:{ln}: line exceeds 120 chars")
    return errors


def main():
    docs = []
    for pattern in ["*.md", "docs/**/*.md"]:
        for p in Path('.').rglob(pattern):
            if p.is_file():
                docs.append(p)
    all_errors = []
    for doc in docs:
        all_errors.extend(lint_file(doc))
    if all_errors:
        print("Markdown lint issues found:")
        for e in all_errors:
            print(" -", e)
        return 1
    print("All markdown docs passed basic lint checks.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
